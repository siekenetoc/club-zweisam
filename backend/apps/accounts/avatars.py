from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps


def _save_variant(image, size, prefix):
    variant = image.copy()
    variant.thumbnail((size, size), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    variant.save(buffer, format="WEBP", quality=86, method=6)
    name = f"avatars/{prefix}-{uuid4().hex}.webp"
    return default_storage.save(name, ContentFile(buffer.getvalue()))


def process_avatar(user, uploaded) -> None:
    old_files = [user.avatar.name, user.avatar_thumb.name]
    image = Image.open(uploaded)
    image.verify()
    image = Image.open(uploaded)
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    user.avatar.name = _save_variant(image, 512, "avatar")
    user.avatar_thumb.name = _save_variant(image, 128, "thumb")
    for name in old_files:
        if name and default_storage.exists(name):
            default_storage.delete(name)


def remove_avatar_files(user) -> None:
    for name in (user.avatar.name, user.avatar_thumb.name):
        if name and default_storage.exists(name):
            default_storage.delete(name)
