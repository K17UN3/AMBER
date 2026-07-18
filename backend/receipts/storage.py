import time
import uuid
from urllib.request import urlopen

import cloudinary.api
import cloudinary.uploader
import cloudinary.utils
from cloudinary.exceptions import NotFound
from django.core.files.base import ContentFile
from django.core.files.storage import Storage


MAX_RECEIPT_BYTES = 10 * 1024 * 1024


class CloudinaryReceiptStorage(Storage):
    """Private Cloudinary storage shared by the API and OCR worker."""

    delivery_type = "authenticated"
    resource_type = "image"
    folder = "amber/receipts"

    def _save(self, name, content):
        result = cloudinary.uploader.upload(
            content,
            resource_type=self.resource_type,
            type=self.delivery_type,
            folder=self.folder,
            public_id=str(uuid.uuid4()),
            use_filename=False,
            unique_filename=False,
            overwrite=False,
        )
        return f"{result['public_id']}.{result['format']}"

    def _open(self, name, mode="rb"):
        if mode not in {"r", "rb"}:
            raise ValueError("Cloudinary receipt storage is read-only when opening files.")

        download_url = self._private_download_url(name)
        with urlopen(download_url, timeout=30) as response:
            data = response.read(MAX_RECEIPT_BYTES + 1)
        if len(data) > MAX_RECEIPT_BYTES:
            raise ValueError("Cloudinary receipt exceeds the 10 MB upload limit.")
        return ContentFile(data, name=name)

    def delete(self, name):
        if not name:
            return
        public_id, _ = self._asset_parts(name)
        cloudinary.uploader.destroy(
            public_id,
            resource_type=self.resource_type,
            type=self.delivery_type,
            invalidate=True,
        )

    def exists(self, name):
        public_id, _ = self._asset_parts(name)
        try:
            cloudinary.api.resource(
                public_id,
                resource_type=self.resource_type,
                type=self.delivery_type,
            )
        except NotFound:
            return False
        return True

    def size(self, name):
        public_id, _ = self._asset_parts(name)
        result = cloudinary.api.resource(
            public_id,
            resource_type=self.resource_type,
            type=self.delivery_type,
        )
        return result["bytes"]

    def url(self, name):
        return self._private_download_url(name)

    def _private_download_url(self, name):
        public_id, image_format = self._asset_parts(name)
        return cloudinary.utils.private_download_url(
            public_id,
            image_format,
            resource_type=self.resource_type,
            type=self.delivery_type,
            expires_at=int(time.time()) + 300,
        )

    @staticmethod
    def _asset_parts(name):
        public_id, separator, image_format = name.rpartition(".")
        if not separator or not public_id or not image_format:
            raise ValueError("Cloudinary receipt name must include an image format.")
        return public_id, image_format
