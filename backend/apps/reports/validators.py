from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image_file(f):
    """Size limit + real content check with Pillow (never trusts extension or Content-Type)."""
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if f.size > limit:
        raise serializers.ValidationError(f"{f.name}: larger than {settings.MAX_UPLOAD_MB} MB.")
    try:
        with Image.open(f) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise serializers.ValidationError(f"{f.name}: not a valid image.")
    finally:
        f.seek(0)
    if fmt not in ALLOWED_FORMATS:
        raise serializers.ValidationError(f"{f.name}: only JPEG, PNG or WebP images are allowed.")


def validate_images(files, existing=0):
    if existing + len(files) > settings.MAX_IMAGES_PER_REPORT:
        raise serializers.ValidationError(f"At most {settings.MAX_IMAGES_PER_REPORT} photos per report.")
    for f in files:
        validate_image_file(f)
