#Receipt scanning: OpenCV pre-processing + Tesseract OCR + amount extraction.

from __future__ import annotations

import argparse
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

TOTAL_KEYWORDS = ("total", "amount due", "balance due", "συνολο", "πληρωτεο", "ποσο πληρωμης")
SKIP_KEYWORDS = ("subtotal", "sub total", "υποσυνολο", "μερικο")

_DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
_AMOUNT_RE = re.compile(r"(?<![\d.,])\d[\d.,]*[.,]\d{2}(?!\d)")


class ReceiptOCRError(RuntimeError):
    "Raised for user-facing OCR problems (missing Tesseract, unreadable image...)."


@dataclass
class ReceiptResult:
    text: str
    amounts: List[float] = field(default_factory=list)
    total: Optional[float] = None


# --------------------------------------------------------------------------- parsing
def _normalise(line: str) -> str:
    """Lower-case and strip accents so 'ΣΎΝΟΛΟ' == 'συνολο'."""
    decomposed = unicodedata.normalize("NFD", line.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").replace("ς", "σ")


def _to_float(token: str) -> float:
    """'1.234,56' / '1,234.56' / '12,50' / '12.50' -> float (last separator is the decimal point)."""
    integer = re.sub(r"[.,]", "", token[:-3])
    return float(f"{integer}.{token[-2:]}")


def find_amounts(text: str) -> List[float]:
    """Return unique monetary amounts found in *text*, in order of appearance."""
    text = _DATE_RE.sub(" ", text)
    amounts = [_to_float(m.group()) for m in _AMOUNT_RE.finditer(text)]
    return list(dict.fromkeys(amounts))


def extract_total(text: str) -> Optional[float]:
    """Best guess for the receipt total, or None if nothing looks like an amount."""
    lines = text.splitlines()
    candidates: List[float] = []
    for i, line in enumerate(lines):
        norm = _normalise(line)
        if any(k in norm for k in SKIP_KEYWORDS):
            continue
        if any(k in norm for k in TOTAL_KEYWORDS):
            found = find_amounts(line)
            if not found and i + 1 < len(lines):  # OCR sometimes splits label and value
                found = find_amounts(lines[i + 1])
            candidates.extend(found)
    if candidates:
        return max(candidates)
    every = find_amounts(text)
    return max(every) if every else None


# --------------------------------------------------------------------------- OCR
def preprocess(image):
    """Grayscale -> upscale small images -> denoise -> Otsu threshold."""
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if gray.shape[0] < 1000:
        scale = 1000 / gray.shape[0]
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def load_image(path: str):
    import cv2
    import numpy as np

    try:  # np.fromfile + imdecode works with Greek / non-ASCII Windows paths; cv2.imread does not
        data = np.fromfile(path, dtype=np.uint8)
    except OSError as exc:
        raise ReceiptOCRError(f"Cannot read file: {exc}") from exc
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ReceiptOCRError("The selected file is not a readable image.")
    return image


def draw_text_boxes(image, lang: str = "eng"):
    """Debug helper (the prototype's bounding-box plot): returns a BGR image with boxes."""
    import cv2
    import pytesseract
    from pytesseract import Output

    canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
    d = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)
    for i in range(len(d["level"])):
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return canvas


def scan_receipt(path: str, lang: str = "ell+eng", tesseract_cmd: Optional[str] = None) -> ReceiptResult:
    """Run OCR on a receipt image and extract amounts / total."""
    try:
        import pytesseract
    except ImportError as exc:
        raise ReceiptOCRError("Receipt scanning needs: pip install opencv-python pytesseract") from exc

    cmd = tesseract_cmd or os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

    image = preprocess(load_image(path))
    try:
        try:
            text = pytesseract.image_to_string(image, lang=lang)
        except pytesseract.TesseractError:
            if lang == "eng":
                raise
            text = pytesseract.image_to_string(image, lang="eng")  # Greek pack not installed
    except pytesseract.TesseractNotFoundError as exc:
        raise ReceiptOCRError(
            "Tesseract OCR is not installed or not on PATH. Install it, or set the "
            "TESSERACT_CMD environment variable to the tesseract executable."
        ) from exc
    return ReceiptResult(text=text, amounts=find_amounts(text), total=extract_total(text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract the total from a receipt image.")
    parser.add_argument("image")
    parser.add_argument("--lang", default="ell+eng")
    args = parser.parse_args()
    result = scan_receipt(args.image, lang=args.lang)
    print(result.text)
    print("=" * 15)
    print("Amounts:", result.amounts)
    print("Total:  ", result.total)


if __name__ == "__main__":
    main()
