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

    # Fallback: for single-column pages that have no Docling table, try pdfplumber
    if pdf_path is not None:
        for pg, rows in list(page_rows.items()):
            if pg in pages_with_docling_table:
                continue  # Docling already found structure here — trust it
            max_cols = max((len(r) for r in rows), default=1)
            if max_cols > 1:
                continue  # already multi-column, fine
            fallback = _pdfplumber_tables_for_page(pdf_path, pg)
            if fallback:
                # Replace the flat text list with the structured table rows
                page_rows[pg] = fallback
                print(f"  [page {pg}] pdfplumber fallback applied ({len(fallback)} rows)")

    return page_rows


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
                    rows = page_rows[pg]
                    max_cols = max((len(r) for r in rows), default=1)
                    padded = [r + [""] * (max_cols - len(r)) for r in rows]
                    df = pd.DataFrame(padded)
                    sheet_name = f"Page_{pg:02d}"
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
            else:
                # Absolute fallback: dump raw text
                text = doc.export_to_text()
                pd.DataFrame({"text": text.splitlines()}).to_excel(
                    writer, sheet_name="Text", index=False
                )

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
