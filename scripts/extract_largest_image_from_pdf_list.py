#!/usr/bin/env python3
"""
Interactive helper: paste PDF paths (one per line), then enter an output folder.
For each PDF (expected single-page), extract the largest embedded image on the page
(or render the page if no embedded image) and save as JPEG named like the PDF.

Dependencies: PyMuPDF (fitz), Pillow
Install: pip install pymupdf pillow
"""
import os
import io
import sys
import traceback

try:
    import fitz
except Exception as e:
    print("Missing dependency: pymupdf (fitz). Install with: pip install pymupdf")
    raise

try:
    from PIL import Image
except Exception as e:
    print("Missing dependency: Pillow. Install with: pip install pillow")
    raise


def normalize_path(p):
    p = p.strip()
    if not p:
        return ''
    p = os.path.expanduser(os.path.expandvars(p))
    # On Windows, allow pasted paths with forward slashes
    p = p.replace('/', os.sep)
    return p


def extract_largest_image_from_pdf(pdf_path, out_path):
    """Return (True, message) on success, (False, error) on failure."""
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return False, f"open_failed: {e}"

    best = None
    try:
        for pno in range(len(doc)):
            page = doc[pno]
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                except Exception:
                    continue
                area = pix.width * pix.height
                if best is None or area > best[0]:
                    best = (area, pno, img, pix)
    except Exception as e:
        doc.close()
        return False, f"scan_failed: {e}"

    try:
        if best is not None:
            area, pno, img, pix = best
            try:
                # CMYK or other color spaces -> convert via fitz to RGB
                if pix.n >= 4:
                    rgb = fitz.Pixmap(fitz.csRGB, pix)
                    img_bytes = rgb.tobytes('png')
                    Image.open(io.BytesIO(img_bytes)).convert('RGB').save(out_path, quality=95)
                    rgb = None
                else:
                    # try to extract original image bytes (may preserve quality)
                    try:
                        imginfo = doc.extract_image(img[0])
                        raw = imginfo.get('image')
                        Image.open(io.BytesIO(raw)).convert('RGB').save(out_path, quality=95)
                    except Exception:
                        # fallback: save pixmap bytes
                        img_bytes = pix.tobytes('png')
                        Image.open(io.BytesIO(img_bytes)).convert('RGB').save(out_path, quality=95)
                return True, f"extracted (area={area})"
            finally:
                try:
                    pix = None
                except Exception:
                    pass
        else:
            # no embedded images found; render first page
            page = doc[0]
            mat = fitz.Matrix(2, 2)
            pixpage = page.get_pixmap(matrix=mat)
            img = Image.frombytes('RGB', [pixpage.width, pixpage.height], pixpage.samples)
            img.save(out_path, quality=95)
            return True, "rendered_page0"
    except Exception as e:
        return False, f"save_failed: {e}\n{traceback.format_exc()}"
    finally:
        try:
            doc.close()
        except:
            pass


if __name__ == '__main__':
    print("Paste PDF file paths (one per line). Submit an empty line when done.")
    paths = []
    while True:
        try:
            line = input().rstrip('\r')
        except EOFError:
            break
        if not line.strip():
            break
        paths.append(normalize_path(line))

    if not paths:
        print("No paths provided. Exiting.")
        sys.exit(0)

    out_dir = input('Enter output folder (will be created if missing): ').strip()
    out_dir = normalize_path(out_dir) or os.path.join(os.getcwd(), 'New folder')
    os.makedirs(out_dir, exist_ok=True)

    print(f"Saving JPEGs into: {out_dir}")

    summary = {'total': 0, 'ok': 0, 'failed': 0, 'skipped_missing': 0}

    for p in paths:
        summary['total'] += 1
        if not os.path.exists(p):
            print(f"MISSING: {p}")
            summary['skipped_missing'] += 1
            continue
        base = os.path.splitext(os.path.basename(p))[0]
        out_name = f"{base}.jpg"
        out_path = os.path.join(out_dir, out_name)
        ok, msg = extract_largest_image_from_pdf(p, out_path)
        if ok:
            print(f"OK: {out_name} <- {p}  ({msg})")
            summary['ok'] += 1
        else:
            print(f"ERR: {out_name} <- {p}  ({msg})")
            summary['failed'] += 1

    print("\nSummary:")
    print(summary)
    print('Done.')
