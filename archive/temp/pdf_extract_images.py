"""Extract images from a PDF using Docling and rename them based on
nearby text (caption / product name found on the same or adjacent page).

Usage:
    python scratch/pdf_extract_images.py "G:\\3D\\60-10 m+m\\m+m-vol.01-accessories\\mpm_v01_accessories.pdf"
    python scratch/pdf_extract_images.py "G:\\3D\\...\\file.pdf" --out "G:\\some\\folder"
    python scratch/pdf_extract_images.py "G:\\3D\\...\\file.pdf" --dry-run

Outputs:
    <out_dir>/  (default: PDF directory / <pdf-stem>_images)
        <01>_<sanitised_name>.png
        <02>_<sanitised_name>.png
        ...
        _image_map.csv    (index,original_docling_ref,page,nearby_text,final_name)

Requirements:
    pip install docling
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitise(text: str, maxlen: int = 60) -> str:
    """Turn arbitrary text into a safe filename token."""
    text = text.strip()
    # Collapse whitespace, replace separators
    text = re.sub(r"[\s/\\:]+", "_", text)
    # Remove characters that are unsafe on Windows
    text = re.sub(r'[<>"|?*]', "", text)
    # Strip leading dots/hyphens
    text = text.lstrip(".-_")
    return text[:maxlen] if text else "unknown"


def _next_text_in_reading_order(
    ordered_items: list[tuple[float, float, str, str]],
    img_t: float,
    img_l: float,
) -> str:
    """Return the first text item that follows the image in reading order.

    ordered_items is a list of (t, l, kind, text) sorted by (t, l).
    kind is 'img' or 'txt'.  img_t/img_l identify the pivot image.
    """
    found_img = False
    for (t, l, kind, text) in ordered_items:
        if not found_img:
            if kind == "img" and abs(t - img_t) < 1.0 and abs(l - img_l) < 1.0:
                found_img = True
            continue
        if kind == "txt" and text:
            return text
    return ""


def _nearest_text(texts_on_page: list[tuple[float, float, str]], img_bbox, max_dist: float = 200.0) -> str:
    """Fallback: return the closest text fragment to img_bbox by Euclidean distance."""
    if not img_bbox or not texts_on_page:
        return ""
    try:
        img_cx = (img_bbox.l + img_bbox.r) / 2
        img_cy = (img_bbox.t + img_bbox.b) / 2
    except Exception:
        return ""

    best_dist = float("inf")
    best_text = ""
    for (ty, tx, txt) in texts_on_page:
        dist = ((tx - img_cx) ** 2 + (ty - img_cy) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_text = txt
    return best_text if best_dist <= max_dist else ""


def _page_no(item) -> int | None:
    prov = getattr(item, "prov", None)
    if prov:
        return getattr(prov[0], "page_no", None)
    return None


def _bbox(item):
    prov = getattr(item, "prov", None)
    if prov:
        return getattr(prov[0], "bbox", None)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("--")]

    if not args:
        print("Usage: python scratch/pdf_extract_images.py <PDF_PATH> [--out <DIR>] [--dry-run]")
        sys.exit(1)

    # Parse --out
    out_dir: Path | None = None
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        out_dir = Path(sys.argv[idx + 1])
        args = [a for a in args if a != sys.argv[idx + 1]]
    
    pdf_path = Path(args[0])
    if not pdf_path.exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    if out_dir is None:
        out_dir = pdf_path.parent / f"{pdf_path.stem}_images"

    print(f"PDF   : {pdf_path}")
    print(f"OutDir: {out_dir}")
    if dry_run:
        print("[DRY-RUN] Files will not be written.\n")

    # ------------------------------------------------------------------
    # Import Docling
    # ------------------------------------------------------------------
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
    except ImportError:
        print("[ERROR] docling is not installed. Run: pip install docling")
        sys.exit(1)

    # Enable image extraction
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 2.0          # 2× resolution for output images
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = True  # extract embedded pictures

    print("Converting PDF with Docling (this may take a minute) ...")
    converter = DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(str(pdf_path))
    doc = result.document

    # ------------------------------------------------------------------
    # Build per-page indexes:
    #   page_texts     : {page: [(cy, cx, text)]}  — for fallback nearest search
    #   page_ro_items  : {page: [(t, l, kind, text)]}  — reading-order list
    # ------------------------------------------------------------------
    page_texts: dict[int, list[tuple[float, float, str]]] = {}
    page_ro_items: dict[int, list[tuple[float, float, str, str]]] = {}

    for item in getattr(doc, "texts", []):
        pg = _page_no(item)
        if pg is None:
            continue
        bb = _bbox(item)
        text = (getattr(item, "text", "") or "").strip()
        if not text:
            continue
        cx = ((bb.l + bb.r) / 2) if bb else 0.0
        cy = ((bb.t + bb.b) / 2) if bb else 0.0
        t = bb.t if bb else 0.0
        l = bb.l if bb else 0.0
        page_texts.setdefault(pg, []).append((cy, cx, text))
        page_ro_items.setdefault(pg, []).append((t, l, "txt", text))

    for pic in getattr(doc, "pictures", []):
        pg = _page_no(pic)
        if pg is None:
            continue
        bb = _bbox(pic)
        t = bb.t if bb else 0.0
        l = bb.l if bb else 0.0
        page_ro_items.setdefault(pg, []).append((t, l, "img", ""))

    # Sort each page's reading-order list by (t, l)
    for pg in page_ro_items:
        page_ro_items[pg].sort(key=lambda x: (x[0], x[1]))

    # ------------------------------------------------------------------
    # Collect pictures from the document
    # ------------------------------------------------------------------
    pictures = list(getattr(doc, "pictures", []))
    print(f"Found {len(pictures)} picture(s) in document.\n")

    if not pictures:
        print("No images extracted. The PDF may be encrypted or image-only.")
        sys.exit(0)

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    map_rows: list[dict] = []
    used_names: dict[str, int] = {}

    for idx, pic in enumerate(pictures, start=1):
        pg = _page_no(pic) or 0
        bb = _bbox(pic)

        # 1. Try caption first (Docling may attach one)
        caption = ""
        cap_obj = getattr(pic, "caption", None)
        if cap_obj:
            caption = (getattr(cap_obj, "text", "") or "").strip()

        # 2. Reading-order: first text that follows this image on the same page
        if not caption:
            bb = _bbox(pic)
            img_t = bb.t if bb else 0.0
            img_l = bb.l if bb else 0.0
            ro = page_ro_items.get(pg, [])
            caption = _next_text_in_reading_order(ro, img_t, img_l)

        # 3. Fall back to nearest text on same page
        if not caption:
            caption = _nearest_text(page_texts.get(pg, []), bb)

        # 4. Last resort: nearest text on adjacent pages
        if not caption:
            for pg_offset in (pg - 1, pg + 1):
                if pg_offset in page_texts:
                    candidate = _nearest_text(page_texts[pg_offset], bb, max_dist=300.0)
                    if candidate:
                        caption = candidate
                        break

        # Build filename
        base_name = _sanitise(caption) if caption else f"image_p{pg:03d}"

        # Deduplicate
        if base_name in used_names:
            used_names[base_name] += 1
            base_name = f"{base_name}_{used_names[base_name]:02d}"
        else:
            used_names[base_name] = 1
            # If it will be reused, we'll suffix from 02 onward
            # (first occurrence keeps no suffix — this is standard behaviour)

        final_name = f"{idx:02d}_{base_name}.png"
        out_path = out_dir / final_name

        print(f"  [{idx:02d}] page={pg}  caption={caption!r}")
        print(f"        → {final_name}")

        map_rows.append({
            "index":        idx,
            "page":         pg,
            "nearby_text":  caption,
            "final_name":   final_name,
        })

        if not dry_run:
            # Save the image — Docling stores it as a PIL Image on .image
            img = getattr(pic, "image", None)
            if img is None:
                print(f"        [WARN] No image data on picture object — skipping")
                continue
            # pic.image may be a Docling ImageRef; get the PIL image
            pil_img = None
            if hasattr(img, "pil_image"):
                pil_img = img.pil_image
            elif hasattr(img, "_pil_image"):
                pil_img = img._pil_image
            elif hasattr(img, "as_pil"):
                pil_img = img.as_pil()
            else:
                # Some versions expose it directly as a PIL Image
                try:
                    import PIL.Image
                    if isinstance(img, PIL.Image.Image):
                        pil_img = img
                except Exception:
                    pass

            if pil_img is None:
                print(f"        [WARN] Could not access PIL image — skipping")
                continue

            pil_img.save(out_path, format="PNG")

    # ------------------------------------------------------------------
    # Write CSV map
    # ------------------------------------------------------------------
    if not dry_run and map_rows:
        csv_path = out_dir / "_image_map.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["index", "page", "nearby_text", "final_name"])
            writer.writeheader()
            writer.writerows(map_rows)
        print(f"\nSaved image map: {csv_path}")

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Done. {len(map_rows)} image(s) processed.")


if __name__ == "__main__":
    main()
