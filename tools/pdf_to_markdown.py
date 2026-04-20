from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def _load_local_env_vars() -> None:
    """Load simple KEY=VALUE pairs from repo .env files into os.environ."""
    repo_root = Path(__file__).resolve().parents[1]
    for env_name in (".env", ".env.local"):
        env_path = repo_root / env_name
        if not env_path.exists() or not env_path.is_file():
            continue
        try:
            for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue


_load_local_env_vars()

OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_VISION_MODEL = os.environ.get("OPENROUTER_VISION_MODEL", "qwen/qwen2.5-vl-72b-instruct")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.environ.get("OPENROUTER_X_TITLE", "pdf-to-markdown")
OPENROUTER_FALLBACK_MODELS = [
    item.strip()
    for item in os.environ.get(
        "OPENROUTER_FALLBACK_MODELS",
        "openai/gpt-4o-mini,qwen/qwen2.5-vl-72b-instruct,deepseek/deepseek-v3.2",
    ).split(",")
    if item.strip()
]
DEFAULT_PDF_ENGINES = ("cloudflare-ai", "auto", "mistral-ocr")


DEFAULT_PROMPT = """You are extracting a product catalogue PDF into markdown.

Return markdown only.
Do not include headings, code fences, commentary, or explanations.
Output one item per line as a two-digit numbered list in this exact style:
01. Product name.
02. Another product name.

Rules:
- Keep each line concise.
- Use the best clean product/object name visible in the PDF.
- Keep brand names when they are part of the visible identification.
- Preserve the reading order of the catalogue.
- Continue numbering sequentially across the whole document.
- End each line with a period.
- If the PDF contains non-product filler or repeated decorative text, omit it.
- First identify the dominant page pattern used by the main catalogue product pages
    (for example: repeated grid/list layout, product hero + caption blocks, or consistent
    product label style).
- Ignore pages that do not match that dominant pattern, including obvious outliers such as
    covers, section dividers, ads, legal/disclaimer pages, contact pages, indexes, blank pages,
    mood/editorial pages, and isolated reference pages.
- Ignore decorative text, page numbers, headers/footers, and running labels that are not
    product names.
- If a page is ambiguous or does not clearly match the dominant product-page pattern,
    skip that page.
- Return only the final markdown list.
"""


NUMBER_TEXT_ONLY_PROMPT = """Extract only explicit numbered catalogue entries from this PDF.

Return markdown only, one line per entry, in this exact style:
01. Text beside number.
02. Text beside number.

Rules:
- Do NOT infer product names from images.
- Use only visible text in the PDF.
- For each visible catalogue item number, copy the text directly beside/associated with that number.
- Keep the original numbering when available.
- If numbering appears as 1, 2, 3, format as 01, 02, 03.
- Ignore unnumbered captions, headers, footers, page numbers, and decorative text.
- Ignore covers/legal/contact/index pages unless they contain numbered catalogue entries.
- If an item number exists but text is unclear, still include the number with best readable text.
- End each line with a period.
"""


def _openrouter_model_candidates(preferred: str | None = None) -> list[str]:
    candidates: list[str] = []
    first = (preferred or "").strip()
    if first and "/" not in first and first != "openrouter/auto":
        first = ""
    if not first:
        first = (OPENROUTER_VISION_MODEL or OPENROUTER_MODEL or "").strip()
    if first:
        candidates.append(first)
    for model_name in OPENROUTER_FALLBACK_MODELS:
        if model_name and model_name not in candidates:
            candidates.append(model_name)
    return candidates


def _pdf_engine_candidates(preferred: str | None = None) -> list[str | None]:
    engine = (preferred or "").strip().lower()
    if not engine or engine == "auto":
        return [None, "cloudflare-ai", "mistral-ocr"]
    candidates: list[str | None] = [engine]
    for fallback_engine in DEFAULT_PDF_ENGINES:
        if fallback_engine != engine:
            candidates.append(fallback_engine)
    return candidates


def _build_headers(api_key: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if OPENROUTER_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_REFERER
    if OPENROUTER_TITLE:
        headers["X-Title"] = OPENROUTER_TITLE
    return headers


def _extract_message_text(body: dict) -> str:
    try:
        content = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    except Exception:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks).strip()
    return str(content).strip()


def _normalize_markdown_list(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:markdown|md)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    normalized: list[str] = []
    counter = 1
    for line in lines:
        match = re.match(r"^(?:[-*]\s*)?(?:\d{1,3}[.):-]\s*)?(.*)$", line)
        content = (match.group(1) if match else line).strip()
        if not content:
            continue
        content = re.sub(r"\s+", " ", content)
        if not content.endswith("."):
            content = f"{content}."
        normalized.append(f"{counter:02d}. {content}")
        counter += 1
    return "\n".join(normalized).strip() + ("\n" if normalized else "")


def _call_openrouter(
    messages: list[dict],
    preferred_model: str | None,
    api_key: str,
    pdf_engine: str | None,
    use_context_compression: bool,
    timeout: int,
) -> tuple[str, dict]:
    headers = _build_headers(api_key)
    last_error = ""
    unavailable_models: list[str] = []
    body: dict = {}

    model_candidates = _openrouter_model_candidates(preferred_model)
    engine_candidates = _pdf_engine_candidates(pdf_engine)

    for index, model_name in enumerate(model_candidates):
        for engine_name in engine_candidates:
            payload: dict = {
                "model": model_name,
                "messages": messages,
                "temperature": 0,
            }
            plugins: list[dict] = []
            if engine_name:
                plugins.append({"id": "file-parser", "pdf": {"engine": engine_name}})
            if use_context_compression:
                plugins.append({"id": "context-compression"})
            if plugins:
                payload["plugins"] = plugins

            req = urllib.request.Request(
                OPENROUTER_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                return _extract_message_text(body), body
            except urllib.error.HTTPError as exc:
                details = ""
                try:
                    details = exc.read().decode("utf-8", errors="replace")[:800]
                except Exception:
                    details = str(exc)
                lower = details.lower()
                model_unavailable = exc.code in {400, 403, 404} and (
                    "not available" in lower or "not found" in lower or "does not exist" in lower
                )
                if model_unavailable:
                    unavailable_models.append(model_name)
                    break
                if exc.code == 402:
                    raise RuntimeError(f"OpenRouter credits exhausted (HTTP 402): {details}") from exc
                last_error = (
                    f"OpenRouter HTTP {exc.code}"
                    f" (model={model_name}, pdf_engine={engine_name or 'auto'}): {details}"
                )
                if exc.code == 400 and "failed to parse" in lower:
                    continue
            except Exception as exc:
                last_error = str(exc)

    tried = ", ".join(unavailable_models) if unavailable_models else "configured models"
    raise RuntimeError(last_error or f"OpenRouter request failed. Tried: {tried}")


def _encode_pdf_data_url(pdf_path: Path) -> str:
    encoded = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")
    return f"data:application/pdf;base64,{encoded}"


def _build_messages(prompt: str, pdf_path: Path) -> list[dict]:
    data_url = _encode_pdf_data_url(pdf_path)
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt.strip()},
                {
                    "type": "file",
                    "file": {
                        "filename": pdf_path.name,
                        "file_data": data_url,
                        "fileData": data_url,
                    },
                },
            ],
        }
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a PDF directly to OpenRouter and save the returned markdown list."
    )
    parser.add_argument("pdf", help="Input PDF path")
    parser.add_argument("--out", help="Output markdown path; defaults beside the PDF")
    parser.add_argument("--model", help="Preferred OpenRouter model id")
    parser.add_argument(
        "--pdf-engine",
        default="cloudflare-ai",
        help="OpenRouter PDF engine: auto, cloudflare-ai, mistral-ocr, or native",
    )
    parser.add_argument("--prompt", help="Inline prompt override")
    parser.add_argument("--prompt-file", help="Path to a text file containing the prompt")
    parser.add_argument(
        "--number-text-only",
        action="store_true",
        help="Extract only explicit numbered entries using visible PDF text (no image inference)",
    )
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds")
    parser.add_argument(
        "--context-compression",
        action="store_true",
        help="Enable OpenRouter context-compression plugin for large inputs",
    )
    parser.add_argument("--stdout-only", action="store_true", help="Print markdown only; do not write file")
    parser.add_argument("--debug-json", help="Optional path to save the raw JSON response")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    pdf_path = Path(args.pdf)
    if not pdf_path.exists() or not pdf_path.is_file():
        print(f"[ERROR] PDF not found: {pdf_path}", file=sys.stderr)
        return 1
    if pdf_path.suffix.lower() != ".pdf":
        print(f"[ERROR] Input must be a .pdf file: {pdf_path}", file=sys.stderr)
        return 1

    api_key = OPENROUTER_API_KEY.strip() or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY is missing.", file=sys.stderr)
        return 1

    prompt = DEFAULT_PROMPT
    if args.number_text_only:
        prompt = NUMBER_TEXT_ONLY_PROMPT
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt

    out_path = Path(args.out) if args.out else pdf_path.with_suffix(".md")

    print(f"PDF: {pdf_path}", file=sys.stderr)
    print(f"Output: {out_path}", file=sys.stderr)
    print(f"Model: {args.model or OPENROUTER_VISION_MODEL}", file=sys.stderr)
    if args.pdf_engine:
        print(f"PDF engine: {args.pdf_engine}", file=sys.stderr)

    try:
        raw_text, response_body = _call_openrouter(
            messages=_build_messages(prompt, pdf_path),
            preferred_model=args.model,
            api_key=api_key,
            pdf_engine=args.pdf_engine,
            use_context_compression=args.context_compression,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    markdown = _normalize_markdown_list(raw_text)
    if not markdown:
        print("[ERROR] Model returned empty content.", file=sys.stderr)
        return 1

    if args.debug_json:
        debug_path = Path(args.debug_json)
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(json.dumps(response_body, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")

    sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())