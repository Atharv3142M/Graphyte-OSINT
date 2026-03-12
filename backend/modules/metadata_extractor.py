"""
Metadata Extractor - EXIF from images, metadata from PDFs.
Extracts OSINT-relevant data: GPS coords, camera info, author, timestamps.
"""
from __future__ import annotations

import base64
import io
import os
from datetime import datetime
from typing import Any

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    Image = None  # type: ignore[assignment,misc]
    TAGS = {}      # type: ignore[assignment]
    GPSTAGS = {}   # type: ignore[assignment]

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[assignment]


def _dms_to_decimal(dms: tuple, ref: str) -> float:
    """Convert GPS DMS (degrees, minutes, seconds) to decimal degrees."""
    try:
        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except (TypeError, ValueError, IndexError):
        return 0.0


def _extract_gps(exif_data: dict) -> dict[str, float] | None:
    """Extract GPS coordinates from EXIF GPS info dict."""
    gps_info = exif_data.get("GPSInfo")
    if not gps_info:
        return None

    # Decode GPSInfo tags
    decoded: dict[str, Any] = {}
    for tag_id, value in gps_info.items():
        tag_name = GPSTAGS.get(tag_id, tag_id)
        decoded[tag_name] = value

    lat = decoded.get("GPSLatitude")
    lat_ref = decoded.get("GPSLatitudeRef", "N")
    lon = decoded.get("GPSLongitude")
    lon_ref = decoded.get("GPSLongitudeRef", "E")

    if lat and lon:
        return {
            "latitude": _dms_to_decimal(lat, lat_ref),
            "longitude": _dms_to_decimal(lon, lon_ref),
        }
    return None


def _extract_image_metadata(img: Any) -> dict[str, Any]:
    """Extract EXIF metadata from a PIL Image object."""
    metadata: dict[str, Any] = {}
    exif_data = img.getexif()

    if not exif_data:
        return {"raw": {}, "gps": None}

    decoded_exif: dict[str, Any] = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        # Convert bytes to string for JSON serialization
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="replace")
            except Exception:
                value = str(value)
        decoded_exif[tag_name] = value

    # Key fields
    metadata["camera_make"] = decoded_exif.get("Make")
    metadata["camera_model"] = decoded_exif.get("Model")
    metadata["software"] = decoded_exif.get("Software")
    metadata["datetime_original"] = decoded_exif.get("DateTimeOriginal")
    metadata["datetime_digitized"] = decoded_exif.get("DateTimeDigitized")
    metadata["datetime_modified"] = decoded_exif.get("DateTime")
    metadata["orientation"] = decoded_exif.get("Orientation")
    metadata["x_resolution"] = decoded_exif.get("XResolution")
    metadata["y_resolution"] = decoded_exif.get("YResolution")
    metadata["exposure_time"] = str(decoded_exif.get("ExposureTime", "")) or None
    metadata["f_number"] = str(decoded_exif.get("FNumber", "")) or None
    metadata["iso"] = decoded_exif.get("ISOSpeedRatings")
    metadata["focal_length"] = str(decoded_exif.get("FocalLength", "")) or None
    metadata["flash"] = decoded_exif.get("Flash")
    metadata["image_width"] = decoded_exif.get("ExifImageWidth") or img.width
    metadata["image_height"] = decoded_exif.get("ExifImageHeight") or img.height
    metadata["color_space"] = decoded_exif.get("ColorSpace")
    metadata["artist"] = decoded_exif.get("Artist")
    metadata["copyright"] = decoded_exif.get("Copyright")
    metadata["description"] = decoded_exif.get("ImageDescription")

    # GPS extraction
    # Re-read with full IFD for GPS data
    full_exif = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        full_exif[tag_name] = value

    # Try to get GPS IFD
    gps = None
    try:
        gps_ifd = exif_data.get_ifd(0x8825)  # GPSInfo IFD
        if gps_ifd:
            full_exif["GPSInfo"] = gps_ifd
            gps = _extract_gps(full_exif)
    except Exception:
        pass

    metadata["gps"] = gps

    # Clean None values for compact output
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return metadata


def _extract_pdf_metadata(reader: Any) -> dict[str, Any]:
    """Extract metadata from a PyPDF2 PdfReader."""
    info = reader.metadata
    if not info:
        return {}

    metadata: dict[str, Any] = {}
    metadata["title"] = info.title
    metadata["author"] = info.author
    metadata["subject"] = info.subject
    metadata["creator"] = info.creator
    metadata["producer"] = info.producer
    metadata["page_count"] = len(reader.pages)

    # Convert dates
    if info.creation_date:
        try:
            metadata["creation_date"] = info.creation_date.isoformat()
        except Exception:
            metadata["creation_date"] = str(info.creation_date)
    if info.modification_date:
        try:
            metadata["modification_date"] = info.modification_date.isoformat()
        except Exception:
            metadata["modification_date"] = str(info.modification_date)

    # Clean None values
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return metadata


def extract_metadata(
    file_path: str | None = None,
    file_base64: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Extract metadata from an image or PDF file.

    Args:
        file_path: Path to a local file.
        file_base64: Base64-encoded file content (alternative to file_path).
        filename: Original filename (used for type detection with base64 input).

    Returns:
        Dict with file_type, metadata fields, GPS coordinates (if image),
        and timestamps.
    """
    if not file_path and not file_base64:
        return {"success": False, "error": "Either file_path or file_base64 is required"}

    # Determine file type from extension
    if file_path:
        name = os.path.basename(file_path)
        ext = os.path.splitext(name)[1].lower()
    elif filename:
        name = filename
        ext = os.path.splitext(filename)[1].lower()
    else:
        name = "unknown"
        ext = ""

    # Get file data
    file_obj = None
    if file_base64:
        try:
            raw = base64.b64decode(file_base64)
            file_obj = io.BytesIO(raw)
        except Exception as e:
            return {"success": False, "error": f"Invalid base64 data: {e}"}
    elif file_path:
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

    image_extensions = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp", ".heic"}
    pdf_extensions = {".pdf"}

    result: dict[str, Any] = {
        "success": True,
        "filename": name,
        "file_type": "unknown",
        "metadata": {},
    }

    if ext in image_extensions:
        if Image is None:
            return {"success": False, "error": "Pillow is not installed. Run: pip install Pillow", "filename": name}
        result["file_type"] = "image"
        try:
            if file_obj:
                img = Image.open(file_obj)
            else:
                img = Image.open(file_path)
            result["metadata"] = _extract_image_metadata(img)
            result["metadata"]["format"] = img.format
            result["metadata"]["mode"] = img.mode
            result["metadata"]["size"] = {"width": img.width, "height": img.height}
            gps = result["metadata"].pop("gps", None)
            result["gps"] = gps
        except Exception as e:
            return {"success": False, "error": f"Failed to read image: {e}", "filename": name}

    elif ext in pdf_extensions:
        if PdfReader is None:
            return {"success": False, "error": "PyPDF2 is not installed. Run: pip install PyPDF2", "filename": name}
        result["file_type"] = "pdf"
        try:
            if file_obj:
                reader = PdfReader(file_obj)
            else:
                reader = PdfReader(file_path)
            result["metadata"] = _extract_pdf_metadata(reader)
            result["gps"] = None
        except Exception as e:
            return {"success": False, "error": f"Failed to read PDF: {e}", "filename": name}

    else:
        # Try image first, then PDF
        if Image is not None:
            try:
                if file_obj:
                    file_obj.seek(0)
                    img = Image.open(file_obj)
                else:
                    img = Image.open(file_path)
                img.verify()
                if file_obj:
                    file_obj.seek(0)
                    img = Image.open(file_obj)
                else:
                    img = Image.open(file_path)
                result["file_type"] = "image"
                result["metadata"] = _extract_image_metadata(img)
                result["metadata"]["format"] = img.format
                result["metadata"]["mode"] = img.mode
                result["metadata"]["size"] = {"width": img.width, "height": img.height}
                gps = result["metadata"].pop("gps", None)
                result["gps"] = gps
                return result
            except Exception:
                pass

        if PdfReader is not None:
            try:
                if file_obj:
                    file_obj.seek(0)
                    reader = PdfReader(file_obj)
                else:
                    reader = PdfReader(file_path)
                result["file_type"] = "pdf"
                result["metadata"] = _extract_pdf_metadata(reader)
                result["gps"] = None
                return result
            except Exception:
                pass

        result["file_type"] = "unsupported"
        result["error"] = f"Unsupported file type: {ext or 'unknown'}"
        result["success"] = False

    return result
