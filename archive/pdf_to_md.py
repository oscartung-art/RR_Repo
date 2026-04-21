"""
PDF to Markdown Converter (Chunked Processing)

This script extracts text from a PDF file page by page and appends it to a Markdown (.md) file.
It is efficient for large PDFs and can be adapted for more advanced formatting.

Dependencies: pdfplumber
Install with: pip install pdfplumber

---

How to Use (Step by Step):

1. Install the required library:
   pip install pdfplumber

2. Place your PDF file in a known location (e.g., D:/RR_Repo/input.pdf).

3. Run the script. It will prompt you for the PDF file path. The output Markdown file will be created in the same location with the same name, but with a .md extension.

---

"""

import pdfplumber
import os


def pdf_to_md(pdf_path, md_path):
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return
    with pdfplumber.open(pdf_path) as pdf, open(md_path, "w", encoding="utf-8") as md_file:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            md_file.write(f"\n\n---\n\n# Page {i}\n\n")
            md_file.write(text)
            print(f"Processed page {i}/{len(pdf.pages)}")
    print(f"Done! Markdown saved to {md_path}")


if __name__ == "__main__":
    pdf_path = input("Enter the path to your PDF file: ").strip().strip('"')
    if not pdf_path.lower().endswith('.pdf'):
        print("Error: Input file must be a .pdf")
    else:
        md_path = os.path.splitext(pdf_path)[0] + ".md"
        pdf_to_md(pdf_path, md_path)
