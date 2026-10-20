from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile

IMAGE_EXTS = frozenset({"jpg", "jpeg", "png", "webp"})

_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def compress_image_file(
    media,
    max_size_mb: float = 0.5,
    max_dimension: int = 1920,
    quality: int = 75,
    threshold_kb: int = 300,
    min_quality: int = 40,
):
    """
    فشرده‌سازی یک فایل تصویری (نسخه مشترک همه اپ‌ها).
    - فقط فایل آپلودشده جدید (UploadedFile) لمس می‌شود؛ FieldFile موجود دست‌نخورده برمی‌گردد.
    - max_size_mb واقعاً اعمال می‌شود: تا رسیدن به سقف، quality پله‌پله کم می‌شود.
    - چرخش EXIF اصلاح، پس‌زمینه شفاف روی سفید composite، content_type و field_name درست.
    - در هر خطا یا بزرگ‌تر شدن خروجی، فایل اصلی برگردانده می‌شود.
    """
    if not media:
        return media

    if not isinstance(media, UploadedFile):
        return media  # فایل موجود دیتابیس؛ دوباره ذخیره نکن

    ext = Path(getattr(media, "name", "") or "").suffix.lower().lstrip(".")
    if ext not in IMAGE_EXTS:
        return media

    try:
        size = media.size
    except Exception:
        return media
    if size <= threshold_kb * 1024:
        try:
            media.seek(0)
        except Exception:
            pass
        return media

    try:
        media.seek(0)
        img = Image.open(media)
        img = ImageOps.exif_transpose(img)

        if max(img.size) > max_dimension:
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS  # type: ignore Pillow قدیمی
            img.thumbnail((max_dimension, max_dimension), resample)

        if ext in ("jpg", "jpeg"):
            if img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                alpha = img.convert("RGBA").split()[-1]
                bg.paste(img.convert("RGB"), mask=alpha)
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
        elif img.mode == "P":
            img = img.convert("RGBA")

        target = int(max_size_mb * 1024 * 1024)
        q = quality
        data: bytes | None = None
        while True:
            output = BytesIO()
            save_kwargs: dict[str, Any] = {"optimize": True}
            if ext in ("jpg", "jpeg"):
                save_kwargs.update({"format": "JPEG", "quality": q})
            elif ext == "webp":
                save_kwargs.update({"format": "WEBP", "quality": q})
            else:  # png: quantize واقعی وگرنه عملاً فشرده نمی‌شود
                save_kwargs.update({"format": "PNG"})
                candidate = img
                if candidate.mode == "RGBA":
                    candidate = candidate.convert("P", palette=Image.ADAPTIVE)
                candidate.save(output, **save_kwargs)
                data = output.getvalue()
                break
            img.save(output, **save_kwargs)
            data = output.getvalue()
            if len(data) <= target or q <= min_quality:
                break
            q = max(min_quality, q - 10)

        assert data is not None
        if len(data) >= size:
            media.seek(0)
            return media

        field_name = getattr(media, "field_name", None) or "image"
        out = BytesIO(data)
        return InMemoryUploadedFile(
            out,
            field_name=field_name,
            name=media.name,
            content_type=_CONTENT_TYPES[ext],
            size=len(data),
            charset=None,
        )
    except Exception:
        try:
            media.seek(0)
        except Exception:
            pass
        return media
