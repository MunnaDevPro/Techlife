import io
import re
import socket
import ipaddress
import urllib.parse
from PIL import Image, ImageOps
import requests

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from blog_post.models import normalize_url

# Limit max pixel count to 10 Megapixels to prevent decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 10_000_000


def is_ip_blocked(ip_str):
    """
    Checks whether an IP address string resolves to a blocked range:
    private, loopback, link-local, multicast, reserved, unspecified, or cloud metadata IPs.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return True

    if (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast or
        ip_obj.is_reserved or ip_obj.is_link_local or ip_obj.is_unspecified or
        not ip_obj.is_global):
        return True

    # Cloud metadata service & private IP protection
    blocked_specific = {"169.254.169.254", "169.254.170.2", "fd00:ec2::2", "100.100.100.200", "127.0.0.1", "::1"}
    if str(ip_obj) in blocked_specific:
        return True

    return False


def validate_url_and_resolve_ips(url_str):
    """
    Validates URL scheme, credentials, ports, and resolves hostnames to verify
    all target IP addresses against SSRF / private network ranges.
    Returns (is_valid, error_code, detail_msg).
    """
    if not url_str or not isinstance(url_str, str):
        return False, "INVALID_IMAGE_URL", "Missing or invalid URL type."

    normalized = normalize_url(url_str)
    if not normalized:
        return False, "INVALID_IMAGE_URL", "Failed to normalize URL."

    try:
        parsed = urllib.parse.urlparse(normalized)
    except Exception:
        return False, "INVALID_IMAGE_URL", "Malformed URL."

    if parsed.scheme not in ('http', 'https'):
        return False, "INVALID_IMAGE_URL", f"Unsupported scheme '{parsed.scheme}'. Only http/https are allowed."

    if parsed.username or parsed.password:
        return False, "INVALID_IMAGE_URL", "Credentials embedded in URL are forbidden."

    if parsed.port and parsed.port not in (80, 443):
        return False, "INVALID_IMAGE_URL", f"Port {parsed.port} is forbidden."

    hostname = parsed.hostname
    if not hostname:
        return False, "INVALID_IMAGE_URL", "Missing hostname in URL."

    # Direct IP literal check or DNS lookup
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if is_ip_blocked(str(ip_obj)):
            return False, "BLOCKED_IMAGE_HOST", f"Blocked IP address range '{hostname}'."
    except ValueError:
        # Resolve hostname DNS records
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not addr_info:
                return False, "INVALID_IMAGE_URL", f"Host '{hostname}' could not be resolved."

            for entry in addr_info:
                ip_str = entry[4][0]
                if is_ip_blocked(ip_str):
                    return False, "BLOCKED_IMAGE_HOST", f"Hostname '{hostname}' resolved to blocked IP '{ip_str}'."
        except Exception:
            return False, "INVALID_IMAGE_URL", f"DNS resolution failed for hostname '{hostname}'."

    return True, None, normalized


def download_and_localize_automation_image(source_url, slug, content_hash):
    """
    Securely downloads, validates, sanitizes, resizes, and converts a source image to WebP,
    saving it to Django default storage under blog_images/.
    Returns (success: bool, rel_path_or_error_code: str, error_message: str).
    """
    max_bytes = getattr(settings, 'AUTOMATION_IMAGE_MAX_BYTES', 8388608)
    connect_timeout = getattr(settings, 'AUTOMATION_IMAGE_CONNECT_TIMEOUT', 5)
    read_timeout = getattr(settings, 'AUTOMATION_IMAGE_READ_TIMEOUT', 15)
    max_redirects = getattr(settings, 'AUTOMATION_IMAGE_MAX_REDIRECTS', 3)
    max_width = getattr(settings, 'AUTOMATION_IMAGE_MAX_WIDTH', 1600)
    max_height = getattr(settings, 'AUTOMATION_IMAGE_MAX_HEIGHT', 1200)
    webp_quality = getattr(settings, 'AUTOMATION_IMAGE_WEBP_QUALITY', 82)

    current_url = source_url
    redirect_count = 0
    downloaded_bytes = bytearray()
    content_type_valid = False

    session = requests.Session()
    session.headers.update({"User-Agent": "TechLife-Automation-ImageFetcher/1.0"})

    while True:
        valid, err_code, res_or_msg = validate_url_and_resolve_ips(current_url)
        if not valid:
            if redirect_count > 0:
                return False, "IMAGE_REDIRECT_BLOCKED", f"Redirect to unsafe location blocked: {res_or_msg}"
            return False, err_code, res_or_msg

        current_url = res_or_msg

        try:
            response = session.get(
                current_url,
                stream=True,
                allow_redirects=False,
                timeout=(connect_timeout, read_timeout)
            )
        except requests.exceptions.Timeout:
            return False, "IMAGE_DOWNLOAD_TIMEOUT", "Image download timed out."
        except requests.exceptions.RequestException as exc:
            return False, "INVALID_IMAGE_URL", f"HTTP request failed: {str(exc)}"

        if response.status_code in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                return False, "IMAGE_REDIRECT_BLOCKED", f"Maximum redirect limit of {max_redirects} exceeded."
            location = response.headers.get("Location")
            if not location:
                return False, "IMAGE_REDIRECT_BLOCKED", "Redirect location header missing."
            current_url = urllib.parse.urljoin(current_url, location)
            continue

        if response.status_code != 200:
            return False, "INVALID_IMAGE_URL", f"Source HTTP request returned status {response.status_code}."

        ct = response.headers.get("Content-Type", "").lower()
        allowed_cts = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if ct and not any(allowed in ct for allowed in allowed_cts):
            return False, "UNSUPPORTED_IMAGE_TYPE", f"Unsupported Content-Type header '{ct}'."

        try:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded_bytes.extend(chunk)
                    if len(downloaded_bytes) > max_bytes:
                        return False, "IMAGE_TOO_LARGE", f"Image size exceeded maximum allowed limit of {max_bytes} bytes."
        except requests.exceptions.RequestException:
            return False, "IMAGE_DOWNLOAD_TIMEOUT", "Connection dropped during image streaming."

        break

    if not downloaded_bytes:
        return False, "INVALID_IMAGE_CONTENT", "Downloaded image payload is empty."

    # Pillow Inspection & Verification
    raw_data = bytes(downloaded_bytes)
    bio = io.BytesIO(raw_data)

    try:
        verify_img = Image.open(bio)
        verify_img.verify()
    except Image.DecompressionBombError:
        return False, "IMAGE_DECOMPRESSION_BOMB", "Image exceeded maximum pixel decompressed safety limit."
    except Exception as exc:
        return False, "INVALID_IMAGE_CONTENT", f"Corrupt or invalid image bytes: {str(exc)}"

    bio.seek(0)
    try:
        img = Image.open(bio)
    except Exception as exc:
        return False, "INVALID_IMAGE_CONTENT", f"Failed to parse image data: {str(exc)}"

    img_format = (img.format or "").upper()
    if img_format not in ("JPEG", "JPG", "PNG", "WEBP"):
        return False, "UNSUPPORTED_IMAGE_TYPE", f"Unsupported image format '{img_format}'. Only JPEG, PNG, and WebP are allowed."

    # Process, Orient, Clean EXIF, Resize, and Convert to WebP
    try:
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        w, h = img.size
        if w > max_width or h > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        clean_img = Image.new(img.mode, img.size)
        clean_img.paste(img)

        out_bio = io.BytesIO()
        clean_img.save(out_bio, format="WEBP", quality=webp_quality)
        webp_bytes = out_bio.getvalue()
    except Image.DecompressionBombError:
        return False, "IMAGE_DECOMPRESSION_BOMB", "Image pixel count exceeded decompression threshold."
    except Exception as exc:
        return False, "INVALID_IMAGE_CONTENT", f"Image processing failed: {str(exc)}"

    # Save via Django default storage
    from django.utils.text import slugify
    safe_slug = slugify(slug)[:40] or "auto-image"
    short_hash = str(content_hash or "hash")[:8]
    rel_path = f"blog_images/{safe_slug}-{short_hash}.webp"

    try:
        saved_path = default_storage.save(rel_path, ContentFile(webp_bytes))
        return True, saved_path, "Image successfully localized and stored."
    except Exception as exc:
        return False, "IMAGE_STORAGE_FAILED", f"Failed to save image to storage backend: {str(exc)}"
