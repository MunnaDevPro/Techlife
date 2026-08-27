import re
import urllib.parse
import unicodedata
from bs4 import BeautifulSoup
from django.conf import settings


# Control character regex (excluding tab \x09, newline \x0a, carriage return \x0d)
CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')

ALLOWED_TAGS = {
    'p', 'br', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'b',
    'em', 'i', 'blockquote', 'a', 'table', 'thead', 'tbody', 'tr',
    'th', 'td', 'code', 'pre', 'hr'
}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title'},
    'th': {'colspan', 'rowspan', 'scope'},
    'td': {'colspan', 'rowspan'}
}

DISALLOWED_TAGS = {
    'script', 'style', 'iframe', 'object', 'embed', 'form', 'input',
    'button', 'svg', 'math', 'video', 'audio', 'img'
}


def clean_text_string(text):
    """
    Strips control characters, null bytes, and normalizes Unicode to NFC.
    """
    if not text or not isinstance(text, str):
        return ""
    # Strip null bytes and control chars
    text = CONTROL_CHAR_RE.sub('', text.replace('\x00', ''))
    # Normalize Unicode
    text = unicodedata.normalize('NFC', text)
    return text.strip()


def strip_html_to_plain_text(html_str):
    """
    Strips all HTML tags and returns clean plain text.
    """
    cleaned = clean_text_string(html_str)
    if not cleaned:
        return ""
    soup = BeautifulSoup(cleaned, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def is_safe_link_url(url_str):
    """
    Validates link URLs against dangerous schemes, obfuscated JavaScript, data URIs, and protocol-relative links.
    Returns (is_safe: bool, normalized_url: str).
    """
    if not url_str or not isinstance(url_str, str):
        return False, ""

    raw = url_str.strip()

    # Reject null bytes, control characters, or line breaks in URL
    if any(c in raw for c in ('\x00', '\r', '\n', '\t')):
        return False, ""

    # Protocol relative check (//evil.com)
    if raw.startswith('//'):
        return False, ""

    # Unescape HTML entities & lowercase for scheme checking
    decoded = urllib.parse.unquote(raw)
    decoded_clean = re.sub(r'\s+', '', decoded).lower()

    # Reject dangerous scheme prefixes
    dangerous_schemes = ('javascript:', 'data:', 'file:', 'ftp:', 'vbscript:', 'blob:')
    for ds in dangerous_schemes:
        if decoded_clean.startswith(ds):
            return False, ""

    # Parse scheme
    try:
        parsed = urllib.parse.urlparse(raw)
    except Exception:
        return False, ""

    scheme = parsed.scheme.lower()
    if scheme and scheme not in ('http', 'https', 'mailto'):
        return False, ""

    # Mailto links
    if scheme == 'mailto':
        return True, raw

    # Default to relative or http/https
    if not scheme and not parsed.netloc:
        # Relative link
        if raw.startswith('/'):
            return True, raw
        return False, ""

    if scheme in ('http', 'https') and parsed.netloc:
        return True, raw

    return False, ""


def sanitize_automation_html_description(html_content):
    """
    Sanitizes article description HTML against strict whitelist rules:
    - Removes scripts, styles, forms, iframes, images, SVG, math, etc.
    - Strips inline styles, classes, IDs, event handlers (on*).
    - Validates links (allows http, https, mailto; forces rel/target on external links).
    - Removes empty headings, empty links, and meaningless empty wrappers.
    - Returns (success, error_code, error_msg, sanitized_html, plain_text).
    """
    cleaned_input = clean_text_string(html_content)
    if not cleaned_input:
        return False, "UNSAFE_OR_EMPTY_CONTENT", "Article content is empty.", "", ""

    soup = BeautifulSoup(cleaned_input, 'html.parser')

    # 1. Completely decompose disallowed tags along with their contents
    for tag_name in DISALLOWED_TAGS:
        for element in soup.find_all(tag_name):
            element.decompose()

    # 2. Process all elements in the tree
    for element in list(soup.find_all(True)):
        tag_name = element.name.lower()

        # If tag is not in whitelist, unwrap structural tags or decompose
        if tag_name not in ALLOWED_TAGS:
            element.unwrap()
            continue

        # Clean attributes
        allowed_attrs = ALLOWED_ATTRIBUTES.get(tag_name, set())
        element_attrs = dict(element.attrs)

        for attr in element_attrs:
            attr_lower = attr.lower()
            # Always drop event handlers (on*), style, class, id, data-*
            if (attr_lower.startswith('on') or attr_lower in ('style', 'class', 'id') or
                attr_lower.startswith('data-') or attr_lower not in allowed_attrs):
                del element[attr]

        # Handle <a> tag links specifically
        if tag_name == 'a':
            href = element.get('href')
            is_safe, norm_url = is_safe_link_url(href)
            if not is_safe:
                return False, "INVALID_LINK", f"Article contains unsafe or malformed link: '{href}'", "", ""

            element['href'] = norm_url

            # Force rel and target for external http/https links
            if norm_url.startswith('http://') or norm_url.startswith('https://'):
                element['rel'] = 'nofollow noopener noreferrer'
                element['target'] = '_blank'

    # 3. Clean up empty elements (headings, links, paragraphs)
    for element in list(soup.find_all(['h2', 'h3', 'h4', 'a', 'p'])):
        if not element.get_text(strip=True) and not element.find_all(['br', 'hr']):
            element.decompose()

    sanitized_html = str(soup).strip()
    plain_text = soup.get_text(separator=' ', strip=True)
    plain_text = clean_text_string(plain_text)

    if not sanitized_html or not plain_text:
        return False, "UNSAFE_OR_EMPTY_CONTENT", "Article content is empty after sanitization.", "", ""

    if len(plain_text) < 150:
        return False, "ARTICLE_TOO_SHORT", f"Article contains only {len(plain_text)} text characters (minimum 150 required).", "", ""

    return True, None, None, sanitized_html, plain_text


def sanitize_automation_payload(payload):
    """
    Sanitizes all text fields in an automation submission.
    Returns (success, error_code, error_msg, sanitized_payload).
    """
    max_bytes = getattr(settings, 'AUTOMATION_ARTICLE_MAX_BYTES', 524288)

    # Check request payload byte size
    raw_desc = str(payload.get('description') or '')
    if len(raw_desc.encode('utf-8')) > max_bytes:
        return False, "ARTICLE_TOO_LARGE", f"Article payload exceeds maximum allowed size of {max_bytes} bytes.", None

    sanitized = dict(payload)

    # Plain text fields
    plain_text_fields = {
        'title': True,
        'subtitle': False,
        'meta_title': False,
        'meta_description': False,
        'review_notes': False,
        'source_name': True,
        'source_author': False,
        'original_title': False,
    }

    for field, is_required in plain_text_fields.items():
        if field in payload and payload[field] is not None:
            cleaned = strip_html_to_plain_text(str(payload[field]))

            if field == 'meta_title' and len(cleaned) > 255:
                cleaned = cleaned[:255].strip()
            elif field == 'meta_description' and len(cleaned) > 500:
                cleaned = cleaned[:500].strip()

            if is_required and not cleaned:
                return False, "INVALID_TEXT_FIELD", f"Field '{field}' cannot be empty.", None

            sanitized[field] = cleaned if cleaned else None

    # HTML Description field
    desc_html = str(payload.get('description') or '')
    success, err_code, err_msg, clean_html, _ = sanitize_automation_html_description(desc_html)
    if not success:
        return False, err_code, err_msg, None

    sanitized['description'] = clean_html

    return True, None, None, sanitized
