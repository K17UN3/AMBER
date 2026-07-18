import json
import os
import re
import tempfile
import unicodedata
from datetime import date
from functools import lru_cache


TOTAL_KEYWORDS = r"(?:合\s*(?:計|言\s*十)|お\s*買\s*上(?:げ)?\s*金\s*額|ご\s*請\s*求\s*額|現\s*計|現\s*金|総\s*額)"
DATE_PATTERN = re.compile(
    r"(?P<year>20\d{2})\s*(?:/|\.|年)\s*(?P<month>\d{1,2})\s*(?:/|\.|月)\s*(?P<day>\d{1,2})(?:日)?"
)


class OCRProcessingError(Exception):
    pass


@lru_cache(maxsize=1)
def get_ocr_engine():
    try:
        from paddleocr import PaddleOCR
    except ImportError as error:
        raise OCRProcessingError("PaddleOCR がインストールされていません。") from error

    try:
        return PaddleOCR(
            lang="japan",
            ocr_version=os.environ.get("PADDLE_OCR_VERSION", "PP-OCRv3"),
            enable_mkldnn=os.environ.get("PADDLE_ENABLE_MKLDNN", "False").lower() == "true",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    except TypeError:
        # PaddleOCR 2.x also supports the Japanese recognition model.
        return PaddleOCR(use_angle_cls=True, lang="japan")


def analyze_receipt(image_path):
    prepared_path = None
    try:
        prepared_path = _prepare_ocr_image(image_path)
        engine = get_ocr_engine()
        result = (
            list(engine.predict(prepared_path))
            if hasattr(engine, "predict")
            else engine.ocr(prepared_path, cls=True)
        )
        lines = _extract_lines(result)
    except OCRProcessingError:
        raise
    except Exception as error:
        raise OCRProcessingError("画像をOCR解析できませんでした。もう一度撮影・アップロードしてください。") from error
    finally:
        if prepared_path and prepared_path != image_path:
            try:
                os.unlink(prepared_path)
            except OSError:
                pass

    raw_text = "\n".join(line["text"] for line in lines)
    return {
        "raw_ocr_text": raw_text,
        "ocr_lines": lines,
        "shop_name": extract_shop_name(lines),
        "purchased_at": extract_purchased_at(raw_text),
        "total_amount": extract_total_amount(raw_text),
    }


def _prepare_ocr_image(image_path, max_side=1600):
    from PIL import Image, ImageOps

    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((max_side, max_side))
        if image.mode != "RGB":
            image = image.convert("RGB")
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temporary_file:
            prepared_path = temporary_file.name
        try:
            image.save(prepared_path, format="JPEG", quality=92, optimize=True)
        except Exception:
            try:
                os.unlink(prepared_path)
            except OSError:
                pass
            raise
    return prepared_path


def _extract_lines(result):
    lines = []
    for page in result:
        if isinstance(page, (list, tuple)):
            for item in page:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                coordinates, recognition = item
                if not isinstance(recognition, (list, tuple)) or len(recognition) != 2:
                    continue
                text, confidence = recognition
                lines.append({"text": str(text), "confidence": float(confidence), "coordinates": coordinates})
            continue

        payload = _result_payload(page)
        values = payload.get("res", payload)
        texts = values.get("rec_texts", [])
        scores = values.get("rec_scores", [])
        boxes = values.get("rec_polys", values.get("rec_boxes", []))
        for index, text in enumerate(texts):
            lines.append(
                {
                    "text": str(text),
                    "confidence": float(scores[index]) if index < len(scores) else None,
                    "coordinates": _json_safe(boxes[index]) if index < len(boxes) else [],
                }
            )
    return lines


def _result_payload(result):
    payload = getattr(result, "json", result)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        return json.loads(payload)
    if hasattr(payload, "to_dict"):
        return payload.to_dict()
    return payload if isinstance(payload, dict) else {}


def _json_safe(value):
    return value.tolist() if hasattr(value, "tolist") else value


def extract_shop_name(lines):
    candidates = []
    for line in lines[:8]:
        text = line["text"].strip()
        if not text or DATE_PATTERN.search(text) or re.search(TOTAL_KEYWORDS, text):
            continue
        if re.search(
            r"(?:TEL|〒|領収書|レシート|営業時間|\d{2,4}[-ー]\d{2,4}|[都道府県市区町丁目番地])",
            text,
            re.IGNORECASE,
        ):
            continue
        if len(re.findall(r"[A-Za-zァ-ヶ一-龯々〆ヵヶ]", text)) < 2:
            continue
        candidates.append(line)
    if not candidates:
        return None
    best = max(candidates, key=lambda line: line.get("confidence") or 0)
    return best["text"].strip()[:255]


def extract_purchased_at(raw_text):
    match = DATE_PATTERN.search(raw_text)
    if not match:
        return None
    try:
        return date(int(match["year"]), int(match["month"]), int(match["day"])).isoformat()
    except ValueError:
        return None


def extract_total_amount(raw_text):
    lines = [unicodedata.normalize("NFKC", line) for line in raw_text.splitlines()]
    for index, line in enumerate(lines):
        if not re.search(TOTAL_KEYWORDS, line):
            continue
        nearby_lines = [line]
        if index > 0:
            nearby_lines.append(lines[index - 1])
        if index + 1 < len(lines):
            nearby_lines.append(lines[index + 1])
        for nearby in nearby_lines:
            amounts = re.findall(
                r"(?:¥|￥)?\s*([0-9]{1,3}(?:[,.][0-9]{3})+|[0-9]+)(?![0-9])",
                nearby,
            )
            if amounts:
                return int(amounts[-1].replace(",", "").replace(".", ""))
    return None
