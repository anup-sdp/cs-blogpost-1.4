import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
# ^ Pillow library for image processing, install with: pip install Pillow, when handling images in FastAPI, you typically receive them as UploadFile.
# the original library, PIL, was discontinued years ago. The community created Pillow as a drop-in replacement.

PROFILE_PICS_DIR = Path("media/profile_pics")


def process_profile_image(content: bytes) -> str:
    """
    It receives the image as raw bytes (usually from UploadFile.read() in FastAPI).
    It returns a filename (string) that you store in your database.
    """
    with Image.open(BytesIO(content)) as original:        
        """
        BytesIO(content) turns raw bytes into a file-like object.
        Image.open() (from Pillow) reads that file-like object as an image.
        The with block ensures the image file is properly closed afterward.
        """
        img = ImageOps.exif_transpose(original)
        """
        Many mobile photos contain EXIF orientation metadata instead of actually rotating the pixels.
        Without this: Some images may appear sideways or upside down.
        exif_transpose(): Reads EXIF rotation info,  Rotates the image correctly, Removes the orientation tag, This prevents weird profile pictures.
        """

        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)
        """
        Resizes the image, Crops it if necessary, Ensures final size is exactly 300x300, It preserves aspect ratio and center-crops if needed.
        Image.Resampling.LANCZOS: High-quality downscaling filter, Produces sharp results, Best choice for profile images
        """
        # Convert to RGB (remove transparency), JPEG does not support transparency.
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = PROFILE_PICS_DIR / filename

        PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)

        img.save(filepath, "JPEG", quality=85, optimize=True)

    return filename

"""
function summary:
✔ Correct orientation
✔ Cropped square
✔ 300x300 size
✔ Converted to JPEG
✔ No transparency
✔ Optimized file size
✔ Unique safe filename
✔ Stored in correct directory
"""

def delete_profile_image(filename: str | None) -> None:
    if filename is None:
        return

    filepath = PROFILE_PICS_DIR / filename
    if filepath.exists():
        filepath.unlink()