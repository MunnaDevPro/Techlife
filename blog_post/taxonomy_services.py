import re
import json
import unicodedata
from django.utils.text import slugify
from django.db import IntegrityError
from blog_post.models import Category, SubCategory
from tags.models import Tag
from blog_post.sanitization_services import clean_text_string

RESERVED_TAGS = {
    'news', 'latest', 'click here', 'read more', 'viral', 'trending',
    'update', 'post', 'article', 'info', 'blog'
}

# Regex to strip emojis and decorative symbols
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE
)


def normalize_tag_name(raw_tag):
    """
    Strips HTML, control chars, emojis, leading hashes, repeated whitespace,
    and surrounding punctuation from tag strings.
    """
    if not raw_tag or not isinstance(raw_tag, str):
        return ""

    text = clean_text_string(raw_tag)
    text = EMOJI_RE.sub('', text)

    # Strip leading # and surrounding punctuation
    text = re.sub(r'^[#\s!.,@:;"\'\-]+|[#\s!.,@:;"\'\-]+$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def resolve_automation_taxonomy(data):
    """
    Deterministically resolves category_slug, subcategory_slug, and tags_list.
    Rules:
    - Direct category/subcategory IDs in payload are forbidden.
    - Category must exist (case-insensitive slug or name search).
    - Subcategory (if supplied) must exist under the resolved parent category.
    - tags_list must contain 3-7 valid unique tags.
    - Maximum 3 new tags created per article.
    Returns (success: bool, err_code: str, err_msg: str, resolved_dict: dict).
    """
    # 1. Forbidden Direct Taxonomy IDs Check
    forbidden_id_fields = ['category', 'category_id', 'subcategory', 'subcategory_id']
    detected_forbidden = [f for f in forbidden_id_fields if f in data]
    if detected_forbidden:
        return False, "DIRECT_TAXONOMY_ID_FORBIDDEN", (
            f"Automation payloads must specify category_slug and subcategory_slug instead of direct IDs. "
            f"Forbidden fields present: {', '.join(detected_forbidden)}"
        ), None

    # 2. Category Resolution
    raw_cat_slug = data.get('category_slug')
    if not raw_cat_slug or not str(raw_cat_slug).strip():
        return False, "UNKNOWN_CATEGORY", "category_slug is required for automation requests.", None

    cat_identifier = clean_text_string(str(raw_cat_slug))
    normalized_cat_slug = slugify(cat_identifier)

    category = Category.objects.filter(slug__iexact=normalized_cat_slug).first()
    if not category:
        category = Category.objects.filter(slug__iexact=cat_identifier).first()
    if not category:
        category = Category.objects.filter(name__iexact=cat_identifier).first()

    if not category:
        return False, "UNKNOWN_CATEGORY", f"The supplied category_slug '{raw_cat_slug}' could not be resolved.", None

    # 3. SubCategory Resolution (Optional)
    raw_subcat_slug = data.get('subcategory_slug')
    subcategory = None
    if raw_subcat_slug and str(raw_subcat_slug).strip():
        sub_identifier = clean_text_string(str(raw_subcat_slug))
        normalized_sub_slug = slugify(sub_identifier)

        # Search SubCategory globally first
        global_sub = SubCategory.objects.filter(slug__iexact=normalized_sub_slug).first()
        if not global_sub:
            global_sub = SubCategory.objects.filter(slug__iexact=sub_identifier).first()
        if not global_sub:
            global_sub = SubCategory.objects.filter(name__iexact=sub_identifier).first()

        if not global_sub:
            return False, "UNKNOWN_SUBCATEGORY", f"The supplied subcategory_slug '{raw_subcat_slug}' could not be resolved.", None

        # Verify parent category match
        if global_sub.category_id != category.id:
            return False, "SUBCATEGORY_CATEGORY_MISMATCH", (
                f"SubCategory '{global_sub.name}' belongs to parent category '{global_sub.category.name}', "
                f"not '{category.name}'."
            ), None

        subcategory = global_sub

    # 4. Tags List Validation & Resolution
    raw_tags = None
    if hasattr(data, 'getlist'):
        tags_from_getlist = data.getlist('tags_list')
        if tags_from_getlist:
            raw_tags = tags_from_getlist

    if raw_tags is None:
        raw_tags = data.get('tags_list')

    if isinstance(raw_tags, str):
        try:
            parsed = json.loads(raw_tags)
            if isinstance(parsed, list):
                raw_tags = parsed
            else:
                raw_tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
        except Exception:
            raw_tags = [t.strip() for t in raw_tags.split(',') if t.strip()]

    if not isinstance(raw_tags, (list, tuple)):
        return False, "INVALID_TAGS_LIST", "tags_list must be a JSON array.", None

    raw_tags = list(raw_tags)

    unique_tags = {}  # lower_key -> normalized_name
    for item in raw_tags:
        norm_name = normalize_tag_name(str(item or ''))
        if not norm_name:
            continue

        lower_key = norm_name.lower()
        if lower_key in RESERVED_TAGS:
            return False, "RESERVED_TAG", f"Tag '{norm_name}' is a reserved or generic word.", None

        if len(norm_name) < 2 or len(norm_name) > 50:
            return False, "INVALID_TAG", f"Tag '{norm_name}' must be between 2 and 50 characters in length.", None

        if lower_key not in unique_tags:
            unique_tags[lower_key] = norm_name

    tag_count = len(unique_tags)
    if tag_count < 3:
        return False, "TOO_FEW_TAGS", f"Article requires between 3 and 7 unique tags (got {tag_count}).", None
    if tag_count > 7:
        return False, "TOO_MANY_TAGS", f"Article requires between 3 and 7 unique tags (got {tag_count}).", None

    # Reused vs New Tag Identification
    reused_tags = []
    new_tags_to_create = []

    for lower_key, norm_name in unique_tags.items():
        tag_slug = slugify(norm_name)
        existing_tag = Tag.objects.filter(slug__iexact=tag_slug).first()
        if not existing_tag:
            existing_tag = Tag.objects.filter(name__iexact=norm_name).first()

        if existing_tag:
            reused_tags.append(existing_tag)
        else:
            new_tags_to_create.append({
                'name': norm_name,
                'slug': tag_slug or lower_key
            })

    if len(new_tags_to_create) > 3:
        return False, "TOO_MANY_NEW_TAGS", (
            f"Automation submissions are restricted to creating a maximum of 3 new tags per article "
            f"({len(new_tags_to_create)} new tags requested: {[t['name'] for t in new_tags_to_create]})."
        ), None

    return True, None, None, {
        'category': category,
        'subcategory': subcategory,
        'reused_tags': reused_tags,
        'new_tags_to_create': new_tags_to_create,
    }


def get_or_create_tag_safely(name, slug):
    """
    Concurrency-safe Tag creation helper using get_or_create and slug fallback.
    """
    safe_slug = slug or slugify(name)
    try:
        tag, created = Tag.objects.get_or_create(
            slug=safe_slug,
            defaults={'name': name}
        )
        return tag
    except IntegrityError:
        tag = Tag.objects.filter(slug=safe_slug).first() or Tag.objects.filter(name__iexact=name).first()
        if tag:
            return tag
        # Retry with unique slug fallback
        alt_slug = f"{safe_slug}-tag"
        tag, _ = Tag.objects.get_or_create(
            name=name,
            defaults={'slug': alt_slug}
        )
        return tag
