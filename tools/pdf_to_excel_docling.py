"""
Usage:
    python tools/pdf_to_excel_docling.py
    # Paste the full path to your PDF when prompted.
    # The Excel file will be saved beside the PDF with the same name.
    # One sheet per page — texts and tables are both included in reading order.
    # pdfplumber is used as a fallback for pages where Docling misses table structure.
"""
from pathlib import Path
import pandas as pd
from collections import defaultdict
from openpyxl.styles import Alignment
import re

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def _page_no(item):
    """Return the 1-based page number for a Docling document item, or None."""
    prov = getattr(item, "prov", None)
    if prov:
        return getattr(prov[0], "page_no", None)
    return None


def _top_y(item):
    """Return a sort key so items appear in reading order within a page."""
    prov = getattr(item, "prov", None)
    if prov:
        bbox = getattr(prov[0], "bbox", None)
        if bbox:
            # negate: higher y-coord = earlier on the page (PDF origin is bottom-left)
            return -getattr(bbox, "t", 0)
    return 0


def _table_rows(table_obj):
    """Convert a Docling table object into a list of row-lists."""
    num_rows = int(getattr(table_obj.data, "num_rows", 0) or 0)
    num_cols = int(getattr(table_obj.data, "num_cols", 0) or 0)
    grid = [["" for _ in range(num_cols)] for _ in range(num_rows)]
    for cell in getattr(table_obj.data, "table_cells", []):
        row = int(getattr(cell, "start_row_offset_idx", 0) or 0)
        col = int(getattr(cell, "start_col_offset_idx", 0) or 0)
        text = (getattr(cell, "text", "") or "").strip()
        if 0 <= row < num_rows and 0 <= col < num_cols:
            grid[row][col] = text
    return grid


def _non_empty_cell_count(rows):
    """Count non-empty cells in a row-list grid."""
    return sum(1 for row in rows for cell in row if str(cell).strip())


def _fill_ratio(rows):
    """Return non-empty / total cell ratio for a row-list grid."""
    total_cells = sum(len(row) for row in rows)
    if total_cells == 0:
        return 0.0
    return _non_empty_cell_count(rows) / total_cells


def _docling_table_rows_for_page(doc, page_no):
    """Collect all Docling table rows for one page with separators."""
    page_rows = []
    page_tables = []
    for table in getattr(doc, "tables", []):
        if _page_no(table) == page_no:
            page_tables.append(table)

    # Keep table order stable top-to-bottom.
    page_tables.sort(key=_top_y)

    for table in page_tables:
        rows = _table_rows(table)
        if rows:
            page_rows.append([])
            page_rows.extend(rows)
            page_rows.append([])
    return page_rows


def _should_prefer_pdfplumber(docling_rows, pdfplumber_rows):
    """Decide whether pdfplumber table rows are structurally better than Docling rows."""
    if not pdfplumber_rows:
        return False
    if not docling_rows:
        return True

    doc_fill = _fill_ratio(docling_rows)
    pdf_fill = _fill_ratio(pdfplumber_rows)
    doc_non_empty = _non_empty_cell_count(docling_rows)
    pdf_non_empty = _non_empty_cell_count(pdfplumber_rows)

    # Prefer pdfplumber if its table is much denser, or materially richer in non-empty cells.
    return (pdf_fill - doc_fill) >= 0.15 or pdf_non_empty > (doc_non_empty * 1.2)


def _looks_numeric(text):
    """Return True for common numeric tokens found in table cells."""
    token = text.strip().replace(",", "")
    if not token:
        return False
    return bool(re.match(r"^[+-]?\d+(?:\.\d+)?$", token))


def _explode_multiline_table_rows(rows):
    """
    Expand rows that contain stacked numeric lines so each value is placed in a separate row/cell.

    When the label column (col 0) has more lines than the value columns, it means the top
    label lines are section headers with no corresponding values.  We bottom-align the value
    lines to the last N labels and emit empty values for the header-only label rows at the top.
    """
    expanded = []
    for row in rows:
        lines_per_cell = [str(cell).splitlines() if str(cell).strip() else [""] for cell in row]
        line_count = max((len(lines) for lines in lines_per_cell), default=1)

        # Only explode rows that likely contain stacked numeric values.
        numeric_line_hits = 0
        for lines in lines_per_cell[1:]:   # skip label column
            if len(lines) < 2:
                continue
            if sum(1 for line in lines if _looks_numeric(line)) >= 2:
                numeric_line_hits += 1

        if line_count <= 1 or numeric_line_hits == 0:
            expanded.append(row)
            continue

        # Maximum number of value lines across all non-label columns.
        val_line_count = max((len(lines) for lines in lines_per_cell[1:]), default=1)
        label_lines = lines_per_cell[0]
        label_line_count = len(label_lines)

        # Offset so value lines align to the bottom of the label list.
        label_offset = label_line_count - val_line_count

        for i in range(line_count):
            new_row = []
            # Label column: emit as-is line by line
            new_row.append(label_lines[i].strip() if i < label_line_count else "")
            # Value columns: bottom-aligned — blank for header-only label rows at the top
            for lines in lines_per_cell[1:]:
                val_idx = i - label_offset
                if val_idx < 0 or val_idx >= len(lines):
                    new_row.append("")
                else:
                    new_row.append(lines[val_idx].strip())
            expanded.append(new_row)

    return expanded


def _pdfplumber_tables_for_page(pdf_path, page_no):
    """
    Use pdfplumber to extract tables from a specific page (1-based).
    Returns a list of row-lists, or empty list if nothing found.
    """
    if pdfplumber is None:
        return []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pg = pdf.pages[page_no - 1]
            tables = pg.extract_tables()
            rows = []
            for table in tables:
                if not table:
                    continue
                rows.append([])  # blank separator before each table
                for row in table:
                    rows.append([str(c) if c is not None else "" for c in row])
                rows.append([])  # blank separator after each table
            return rows
    except Exception:
        return []


def _build_page_rows(doc, pdf_path=None):
    """
    Collect all content keyed by page number in reading order.
    Returns dict[page_no] -> list of row-lists ready for DataFrame.
    """
    items = []
    for t in getattr(doc, "texts", []):
        pg = _page_no(t)
        if pg is not None:
            items.append((pg, _top_y(t), "text", t))
    for t in getattr(doc, "tables", []):
        pg = _page_no(t)
        if pg is not None:
            items.append((pg, _top_y(t), "table", t))

    items.sort(key=lambda x: (x[0], x[1]))

    # Track which pages have a Docling-detected table
    pages_with_docling_table = set()
    for t in getattr(doc, "tables", []):
        pg = _page_no(t)
        if pg is not None:
            pages_with_docling_table.add(pg)

    page_rows = defaultdict(list)
    for pg, _, kind, item in items:
        if kind == "text":
            text = (getattr(item, "text", "") or "").strip()
            if text:
                page_rows[pg].append([text])
        else:
            rows = _table_rows(item)
            if rows:
                page_rows[pg].append([])
                page_rows[pg].extend(rows)
                page_rows[pg].append([])

    # Fallback/override: use pdfplumber table rows when they look structurally better.
    if pdf_path is not None:
        for pg, rows in list(page_rows.items()):
            fallback = _pdfplumber_tables_for_page(pdf_path, pg)
            if not fallback:
                continue

            docling_table_rows = _docling_table_rows_for_page(doc, pg)
            max_cols = max((len(r) for r in rows), default=1)

            # Keep old behavior for flat pages with no detected Docling table.
            if pg not in pages_with_docling_table and max_cols <= 1:
                page_rows[pg] = fallback
                print(f"  [page {pg}] pdfplumber fallback applied ({len(fallback)} rows)")
                continue

            # New behavior: if Docling found a table but structure is poor, prefer pdfplumber.
            if _should_prefer_pdfplumber(docling_table_rows, fallback):
                page_rows[pg] = fallback
                print(f"  [page {pg}] pdfplumber table override applied ({len(fallback)} rows)")

    return page_rows


def _format_sheet(worksheet):
    """Apply light formatting for readability in Excel output."""
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for column_cells in worksheet.columns:
        max_len = 0
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            # Use longest visual line in multiline cells for better width estimation.
            line_len = max((len(line) for line in value.splitlines()), default=0)
            max_len = max(max_len, line_len)
        col_letter = column_cells[0].column_letter
        worksheet.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 80)


def main():
    import sys
    if DocumentConverter is None:
        print("Docling is not installed correctly. Run: pip install docling[pdf,excel]")
        return

    if len(sys.argv) >= 2:
        pdf_path = sys.argv[1].strip().strip('"')
    else:
        pdf_path = input("Paste the full path to your PDF file: ").strip().strip('"')
    pdf = Path(pdf_path)
    if not pdf.exists() or pdf.suffix.lower() != ".pdf":
        print(f"File not found or not a PDF: {pdf}")
        return

    if len(sys.argv) >= 3:
        out_path = Path(sys.argv[2].strip().strip('"'))
    else:
        out_path = pdf.with_suffix(".xlsx")
    print(f"Converting {pdf} -> {out_path} ...")

    try:
        converter = DocumentConverter()
        result = converter.convert(str(pdf))
        doc = result.document

        page_rows = _build_page_rows(doc, pdf_path=pdf)
        total_pages = len(getattr(doc, "pages", {})) or (max(page_rows.keys()) if page_rows else 0)

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            if page_rows:
                for pg in sorted(page_rows.keys()):
                    rows = _explode_multiline_table_rows(page_rows[pg])
                    max_cols = max((len(r) for r in rows), default=1)
                    padded = [r + [""] * (max_cols - len(r)) for r in rows]
                    df = pd.DataFrame(padded)
                    sheet_name = f"Page_{pg:02d}"
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    _format_sheet(writer.sheets[sheet_name])
            else:
                # Absolute fallback: dump raw text
                text = doc.export_to_text()
                pd.DataFrame({"text": text.splitlines()}).to_excel(
                    writer, sheet_name="Text", index=False
                )
                _format_sheet(writer.sheets["Text"])

        pages_written = len(page_rows)
        if out_path.exists():
            print(f"Done! {pages_written}/{total_pages} pages written -> {out_path}")
            if pages_written < total_pages:
                missing = sorted(
                    set(range(1, total_pages + 1)) - set(page_rows.keys())
                )
                print(f"  Pages with no extractable content (blank/image-only): {missing}")
        else:
            print("Conversion finished but output file was not created.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
