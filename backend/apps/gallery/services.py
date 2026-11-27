from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps


def process_gallery_image(uploaded):
    image = Image.open(uploaded)
    image.verify()
    image = Image.open(uploaded)
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    if max(width, height) > 1600:
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        width, height = image.size
    main_buffer = BytesIO()
    image.save(main_buffer, format="WEBP", quality=84, method=6)
    main_name = f"gallery/{uuid4().hex}.webp"
    main_name = default_storage.save(main_name, ContentFile(main_buffer.getvalue()))
    thumb = image.copy()
    thumb.thumbnail((480, 480), Image.Resampling.LANCZOS)
    thumb_buffer = BytesIO()
    thumb.save(thumb_buffer, format="WEBP", quality=80, method=6)
    thumb_name = f"gallery/thumbs/{uuid4().hex}.webp"
    thumb_name = default_storage.save(thumb_name, ContentFile(thumb_buffer.getvalue()))
    return main_name, thumb_name, width, height


def delete_gallery_image(image):
    for field in (image.image, image.thumb):
        if field.name and default_storage.exists(field.name):
            default_storage.delete(field.name)
