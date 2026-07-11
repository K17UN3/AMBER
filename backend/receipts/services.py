import json
import re
from datetime import date
from functools import lru_cache


TOTAL_KEYWORDS = r"(?:合計|お買上(?:げ)?金額|ご請求額|現計|現金|総額)"
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
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    except TypeError:
        # PaddleOCR 2.x also supports the Japanese recognition model.
        return PaddleOCR(use_angle_cls=True, lang="japan")


def analyze_receipt(image_path):
    engine = get_ocr_engine()
    try:
        result = list(engine.predict(image_path)) if hasattr(engine, "predict") else engine.ocr(image_path, cls=True)
        lines = _extract_lines(result)
    except OCRProcessingError:
        raise
    except Exception as error:
        raise OCRProcessingError("画像をOCR解析できませんでした。もう一度撮影・アップロードしてください。") from error

    raw_text = "\n".join(line["text"] for line in lines)
    return {
        "raw_ocr_text": raw_text,
        "ocr_lines": lines,
        "shop_name": extract_shop_name(lines),
        "purchased_at": extract_purchased_at(raw_text),
        "total_amount": extract_total_amount(raw_text),
    }


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
    for line in lines[:8]:
        text = line["text"].strip()
        if not text or DATE_PATTERN.search(text) or re.search(TOTAL_KEYWORDS, text):
            continue
        if re.search(r"(?:TEL|〒|領収書|レシート)", text, re.IGNORECASE):
            continue
        return text[:255]
    return None


def extract_purchased_at(raw_text):
    match = DATE_PATTERN.search(raw_text)
    if not match:
        return None
    try:
        return date(int(match["year"]), int(match["month"]), int(match["day"])).isoformat()
    except ValueError:
        return None


def extract_total_amount(raw_text):
    for line in raw_text.splitlines():
        if not re.search(TOTAL_KEYWORDS, line):
            continue
        amounts = re.findall(r"(?:¥|￥)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?![0-9])", line)
        if amounts:
            return int(amounts[-1].replace(",", ""))
    return None
