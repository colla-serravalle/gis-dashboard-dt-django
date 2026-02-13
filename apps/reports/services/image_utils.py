"""Image processing utilities for PDF generation."""

import base64
import io
import logging
import mimetypes
import os

from PIL import Image, ImageOps

from apps.core.services.arcgis import get_arcgis_service

logger = logging.getLogger(__name__)


def fix_exif_orientation(image_bytes):
    """
    Fix EXIF orientation of an image.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        Corrected image bytes (JPEG, quality=85), or original bytes on failure.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)

        # Convert to RGB if necessary (e.g. RGBA PNGs)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except Exception:
        logger.debug("Could not fix EXIF orientation, returning original bytes")
        return image_bytes


def resize_image(image_bytes, max_width=800):
    """
    Resize an image to a maximum width, preserving aspect ratio.

    Args:
        image_bytes: Raw image bytes.
        max_width: Maximum width in pixels.

    Returns:
        Resized image bytes (JPEG), or original bytes if already small enough or on error.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        if img.width <= max_width:
            return image_bytes

        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except Exception:
        logger.debug("Could not resize image, returning original bytes")
        return image_bytes


def image_bytes_to_base64_uri(image_bytes, content_type='image/jpeg'):
    """
    Convert raw image bytes to a base64 data URI string.

    Returns:
        String like 'data:image/jpeg;base64,/9j/4AAQ...'
    """
    encoded = base64.b64encode(image_bytes).decode('ascii')
    return f"data:{content_type};base64,{encoded}"


def fetch_attachment_as_base64(layer_id, object_id, attachment_id, fix_orientation=True):
    """
    Fetch an attachment from ArcGIS and return it as a base64 data URI.

    Args:
        layer_id: ArcGIS layer index.
        object_id: Feature OBJECTID.
        attachment_id: Attachment ID.
        fix_orientation: Whether to fix EXIF orientation.

    Returns:
        Base64 data URI string, or None on failure.
    """
    try:
        service = get_arcgis_service()
        content, content_type = service.get_attachment_content(layer_id, object_id, attachment_id)

        if content is None:
            return None

        if fix_orientation:
            content = fix_exif_orientation(content)

        content = resize_image(content)

        return image_bytes_to_base64_uri(content, 'image/jpeg')
    except Exception:
        logger.exception(f"Failed to fetch attachment {attachment_id} from layer {layer_id}/{object_id}")
        return None


def local_image_to_base64_uri(file_path):
    """
    Read a local image file and return it as a base64 data URI.

    Args:
        file_path: Absolute path to the image file.

    Returns:
        Base64 data URI string, or None if the file doesn't exist.
    """
    if not os.path.exists(file_path):
        logger.warning(f"Local image not found: {file_path}")
        return None

    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'image/png'

    with open(file_path, 'rb') as f:
        image_bytes = f.read()

    return image_bytes_to_base64_uri(image_bytes, content_type)
