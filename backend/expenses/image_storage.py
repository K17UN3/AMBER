import logging
from uuid import uuid4

import cloudinary.uploader
from django.conf import settings


logger = logging.getLogger(__name__)
MAX_IMAGE_SIZE = 10 * 1024 * 1024


class ImageValidationError(Exception):
    pass


class ImageStorageError(Exception):
    pass


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
            public_id=f"amber/receipts/{user_id}/{uuid4().hex}",
            overwrite=False,
        )
    except Exception as exc:
        logger.exception("Cloudinary receipt upload failed")
        raise ImageStorageError("画像の保存に失敗しました。しばらくしてから再度お試しください。") from exc

    secure_url = result.get("secure_url")
    public_id = result.get("public_id")
    if not secure_url or not public_id:
        logger.error("Cloudinary upload response was missing secure_url or public_id")
        raise ImageStorageError("画像の保存に失敗しました。しばらくしてから再度お試しください。")

    return secure_url, public_id


def delete_receipt_image(public_id):
    if not public_id:
        return

    try:
        cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            invalidate=True,
        )
    except Exception:
        logger.exception("Cloudinary receipt cleanup failed for public_id=%s", public_id)
