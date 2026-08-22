import logging
from dataclasses import dataclass
from time import time
from uuid import uuid4

import cloudinary.uploader
from cloudinary.utils import private_download_url
from django.conf import settings


logger = logging.getLogger(__name__)
MAX_IMAGE_SIZE = 10 * 1024 * 1024
SIGNED_URL_TTL_SECONDS = 5 * 60


class ImageValidationError(Exception):
    pass


class ImageStorageError(Exception):
    pass


@dataclass(frozen=True)
class StoredReceiptImage:
    url: str
    public_id: str
    format: str


def upload_receipt_image(image, user_id):
    content_type = getattr(image, "content_type", "") or ""
    if not content_type.startswith("image/"):
        raise ImageValidationError("画像ファイルを選択してください。")
    if image.size > MAX_IMAGE_SIZE:
        raise ImageValidationError("画像サイズは10MB以下にしてください。")
    if not settings.CLOUDINARY_URL:
        raise ImageStorageError("画像保存サービスが設定されていません。")

    try:
        result = cloudinary.uploader.upload(
            image,
            resource_type="image",
            type="authenticated",
            public_id=f"amber/receipts/{user_id}/{uuid4().hex}",
            overwrite=False,
        )
    except Exception as exc:
        logger.exception("Cloudinary receipt upload failed")
        raise ImageStorageError("画像の保存に失敗しました。しばらくしてから再度お試しください。") from exc

    secure_url = result.get("secure_url")
    public_id = result.get("public_id")
    image_format = result.get("format")
    if not secure_url or not public_id or not image_format:
        logger.error("Cloudinary upload response was missing secure_url, public_id, or format")
        raise ImageStorageError("画像の保存に失敗しました。しばらくしてから再度お試しください。")

    return StoredReceiptImage(url=secure_url, public_id=public_id, format=image_format)


def signed_receipt_image_url(public_id, image_format):
    if not public_id or not image_format or not settings.CLOUDINARY_URL:
        return ""

    try:
        return private_download_url(
            public_id,
            image_format,
            resource_type="image",
            type="authenticated",
            expires_at=int(time()) + SIGNED_URL_TTL_SECONDS,
            attachment=False,
        )
    except Exception:
        logger.exception("Cloudinary receipt URL signing failed for public_id=%s", public_id)
        return ""


def delete_receipt_image(public_id):
    if not public_id:
        return

    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            type="authenticated",
            invalidate=True,
        )
    except Exception:
        logger.exception("Cloudinary receipt cleanup failed for public_id=%s", public_id)
