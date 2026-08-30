import re
import time
import urllib.parse
from datetime import datetime, timedelta, time as dtime
import zoneinfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.response import Response
from rest_framework import status

from blog_post.models import BlogPost, Category, SubCategory, AutomationPublishLog, normalize_url
from blog_post.image_services import download_and_localize_automation_image
from blog_post.sanitization_services import sanitize_automation_payload, clean_text_string
from blog_post.taxonomy_services import resolve_automation_taxonomy, get_or_create_tag_safely


def is_valid_http_url(url_str):
    if not url_str or not isinstance(url_str, str):
        return False
    normalized = normalize_url(url_str)
    if not normalized:
        return False
    try:
        parsed = urllib.parse.urlparse(normalized)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
    except Exception:
        return False


def get_asia_dhaka_day_range(now_dt=None):
    if now_dt is None:
        now_dt = timezone.now()

    tz_name = getattr(settings, 'TECHLIFE_AUTOMATION_TIMEZONE', 'Asia/Dhaka') or 'Asia/Dhaka'
    try:
        dhaka_tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        dhaka_tz = zoneinfo.ZoneInfo('Asia/Dhaka')

    local_dt = now_dt.astimezone(dhaka_tz)
    local_start = datetime.combine(local_dt.date(), dtime.min, tzinfo=dhaka_tz)
    local_end = datetime.combine(local_dt.date(), dtime.max, tzinfo=dhaka_tz)
    return local_start, local_end


def sanitize_error_summary(summary):
    if not summary:
        return ""
    text = str(summary)
    text = re.sub(r'Automation\s+[A-Za-z0-9_\-\.\=]+', 'Automation [REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.\=]+', 'Bearer [REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'Token\s+[A-Za-z0-9_\-\.\=]+', 'Token [REDACTED]', text, flags=re.IGNORECASE)
    return text[:500]


def record_automation_log(
    event_type,
    http_status,
    automation_id=None,
    source_name=None,
    source_url=None,
    post=None,
    result_code=None,
    duration_ms=None,
    image_status=None,
    review_decision=None,
    quality_score=None,
    factual_accuracy_score=None,
    language_score=None,
    seo_score=None,
    error_summary="",
    # --- User-token specific (nullable, backward-compat) ---
    auth_source=None,
    token_user=None,
    token_id=None,
    source_ip=None,
):
    try:
        return AutomationPublishLog.objects.create(
            automation_id=automation_id,
            source_name=source_name,
            source_url=source_url,
            post=post,
            event_type=event_type,
            result_code=result_code,
            http_status=http_status,
            duration_ms=duration_ms,
            image_status=image_status,
            review_decision=review_decision,
            quality_score=quality_score,
            factual_accuracy_score=factual_accuracy_score,
            language_score=language_score,
            seo_score=seo_score,
            error_summary=sanitize_error_summary(error_summary),
            auth_source=auth_source,
            token_user=token_user,
            token_id=token_id,
            source_ip=source_ip,
        )
    except Exception:
        return None


def process_automation_post_creation(data, user):
    """
    Ingests automation metadata, enforces early idempotency, emergency shutdown,
    hourly throttling, and daily Bangladesh publication limit guardrails,
    evaluates approval gates, resolves taxonomy, sanitizes payload, processes images,
    and records audit log entries for all automation events.
    """
    start_time = time.time()

    # 1. Extract Identifiers & Normalize for Logging & Idempotency
    raw_auto_id = data.get('automation_id')
    auto_id = clean_text_string(str(raw_auto_id)) if raw_auto_id is not None and str(raw_auto_id).strip() else None

    raw_src_url = data.get('source_url')
    src_url = normalize_url(raw_src_url) if raw_src_url else None

    raw_hash = data.get('original_content_hash')
    content_hash = clean_text_string(str(raw_hash)).lower() if raw_hash is not None and str(raw_hash).strip() else None

    raw_source_name = str(data.get('source_name') or '').strip()
    clean_src_name = clean_text_string(raw_source_name) if raw_source_name else None

    def parse_score(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    quality_score = parse_score(data.get('quality_score'))
    factual_accuracy_score = parse_score(data.get('factual_accuracy_score'))
    language_score = parse_score(data.get('language_score'))
    seo_score = parse_score(data.get('seo_score'))
    review_decision = clean_text_string(str(data.get('review_decision') or ''))

    def log_and_respond(event_type, http_status, resp_dict, post=None, result_code=None, err_summary="", img_status=None):
        dur_ms = int((time.time() - start_time) * 1000)
        code = result_code or resp_dict.get("code") or resp_dict.get("status")
        record_automation_log(
            event_type=event_type,
            http_status=http_status,
            automation_id=auto_id,
            source_name=clean_src_name,
            source_url=src_url,
            post=post,
            result_code=code,
            duration_ms=dur_ms,
            image_status=img_status,
            review_decision=review_decision or None,
            quality_score=quality_score,
            factual_accuracy_score=factual_accuracy_score,
            language_score=language_score,
            seo_score=seo_score,
            error_summary=err_summary or resp_dict.get("message", ""),
        )
        return Response(resp_dict, status=http_status)

    # 1. Forbidden Fields Check
    forbidden_fields = ['author', 'author_id', 'status', 'views', 'is_featured']
    detected_forbidden = [f for f in forbidden_fields if f in data]
    if detected_forbidden:
        return log_and_respond(
            "rejected",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                "status": "rejected",
                "code": "AUTOMATION_FORBIDDEN_FIELDS",
                "message": f"Automation payloads must not specify internal fields: {', '.join(detected_forbidden)}"
            }
        )

    # 2. Idempotency Search (Early exit before quota checks or payload sanitization)
    posts_by_auto_id = list(BlogPost.objects.filter(automation_id=auto_id)) if auto_id else []
    posts_by_url = list(BlogPost.objects.filter(source_url=src_url)) if src_url else []
    posts_by_hash = list(BlogPost.objects.filter(original_content_hash=content_hash)) if content_hash else []

    all_matched = posts_by_auto_id + posts_by_url + posts_by_hash
    matched_ids = set(p.id for p in all_matched)

    if len(matched_ids) > 1:
        return log_and_respond(
            "conflict",
            status.HTTP_409_CONFLICT,
            {
                "status": "conflict",
                "code": "AUTOMATION_IDEMPOTENCY_CONFLICT",
                "message": "Automation identifiers resolve to different posts."
            }
        )

    if len(matched_ids) == 1:
        existing_post = BlogPost.objects.get(id=list(matched_ids)[0])
        return log_and_respond(
            "idempotent_replay",
            status.HTTP_200_OK,
            {
                "status": existing_post.status,
                "post_id": existing_post.id,
                "slug": existing_post.slug,
                "idempotent_replay": True
            },
            post=existing_post,
            result_code="AUTOMATION_IDEMPOTENT_REPLAY"
        )

    # 3. Emergency Switch Check
    is_enabled = getattr(settings, 'TECHLIFE_AUTOMATION_ENABLED', True)
    if not is_enabled:
        return log_and_respond(
            "disabled",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {
                "status": "disabled",
                "code": "AUTOMATION_DISABLED",
                "message": "Automated publishing is temporarily disabled."
            }
        )

    # 4. Hourly Request Throttle Check
    hourly_limit = getattr(settings, 'TECHLIFE_AUTOMATION_HOURLY_REQUEST_LIMIT', 20)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_requests_count = AutomationPublishLog.objects.filter(created_at__gte=one_hour_ago).count()
    if recent_requests_count >= hourly_limit:
        return log_and_respond(
            "throttled",
            status.HTTP_429_TOO_MANY_REQUESTS,
            {
                "status": "throttled",
                "code": "AUTOMATION_REQUEST_RATE_LIMITED",
                "message": "Too many automation requests were received."
            }
        )

    # 5. Bangladesh Daily Quota Check
    daily_limit = getattr(settings, 'TECHLIFE_AUTOMATION_DAILY_POST_LIMIT', 4)
    local_start, local_end = get_asia_dhaka_day_range()

    with transaction.atomic():
        published_today = AutomationPublishLog.objects.select_for_update().filter(
            event_type='published',
            created_at__range=(local_start, local_end)
        ).count()

        if published_today >= daily_limit:
            return log_and_respond(
                "throttled",
                status.HTTP_429_TOO_MANY_REQUESTS,
                {
                    "status": "throttled",
                    "code": "DAILY_PUBLISH_LIMIT_REACHED",
                    "daily_limit": daily_limit,
                    "published_today": published_today,
                    "message": "The daily automated publishing limit has been reached."
                }
            )

    # 6. Gate Validation
    failed_gates = []
    raw_title = str(data.get('title') or '').strip()
    raw_description = str(data.get('description') or '').strip()

    if not raw_title:
        failed_gates.append('title')
    if not raw_description:
        failed_gates.append('description')

    gen_ai = data.get('generated_by_ai')
    if gen_ai not in [True, 'true', 'True', 1]:
        failed_gates.append('generated_by_ai')

    if not auto_id:
        failed_gates.append('automation_id')

    if not clean_src_name:
        failed_gates.append('source_name')

    if not src_url or not is_valid_http_url(src_url):
        failed_gates.append('source_url')

    if not content_hash or not re.match(r'^[a-f0-9]{64}$', content_hash):
        failed_gates.append('original_content_hash')

    ai_model = clean_text_string(str(data.get('ai_model') or ''))
    if not ai_model:
        failed_gates.append('ai_model')

    reviewer_model = clean_text_string(str(data.get('reviewer_model') or ''))
    if not reviewer_model:
        failed_gates.append('reviewer_model')

    if review_decision != 'approved':
        failed_gates.append('review_decision')

    if quality_score is None or quality_score < 90 or quality_score > 100:
        failed_gates.append('quality_score')

    if factual_accuracy_score is None or factual_accuracy_score < 95 or factual_accuracy_score > 100:
        failed_gates.append('factual_accuracy_score')

    if language_score is None or language_score < 90 or language_score > 100:
        failed_gates.append('language_score')

    if seo_score is None or seo_score < 80 or seo_score > 100:
        failed_gates.append('seo_score')

    if failed_gates:
        return log_and_respond(
            "rejected",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                "status": "rejected",
                "code": "AUTOMATION_APPROVAL_FAILED",
                "failed_gates": failed_gates,
                "message": "Article did not satisfy the automated publishing policy."
            },
            err_summary=f"Failed approval gates: {', '.join(failed_gates)}"
        )

    # 7. Taxonomy Resolution
    tax_success, tax_err_code, tax_err_msg, resolved_tax = resolve_automation_taxonomy(data)
    if not tax_success:
        return log_and_respond(
            "rejected",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                "status": "rejected",
                "code": "AUTOMATION_TAXONOMY_INVALID",
                "taxonomy_error": tax_err_code,
                "message": tax_err_msg
            },
            err_summary=f"{tax_err_code}: {tax_err_msg}"
        )

    category = resolved_tax['category']
    subcategory = resolved_tax['subcategory']

    # 8. Content & HTML Sanitization
    san_success, san_err_code, san_err_msg, sanitized_data = sanitize_automation_payload(data)
    if not san_success:
        return log_and_respond(
            "rejected",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                "status": "rejected",
                "code": "AUTOMATION_CONTENT_INVALID",
                "content_error": san_err_code,
                "message": f"The generated article content could not be safely published: {san_err_msg}"
            },
            err_summary=f"{san_err_code}: {san_err_msg}"
        )

    clean_title = sanitized_data['title']
    clean_description = sanitized_data['description']
    clean_subtitle = sanitized_data.get('subtitle')
    clean_meta_title = sanitized_data.get('meta_title')
    clean_meta_description = sanitized_data.get('meta_description')
    clean_source_name = sanitized_data.get('source_name')
    clean_source_author = sanitized_data.get('source_author')
    clean_original_title = sanitized_data.get('original_title')
    clean_review_notes = sanitized_data.get('review_notes')

    # 9. Source Image Download & Localization
    raw_img_url = data.get('source_image_url')
    source_img_url = str(raw_img_url).strip() if raw_img_url else None

    featured_image_path = None
    image_proc_status = "pending"

    if source_img_url:
        temp_slug = slugify(clean_title)
        img_success, path_or_code, err_msg = download_and_localize_automation_image(
            source_img_url, temp_slug, content_hash
        )
        if not img_success:
            return log_and_respond(
                "rejected",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {
                    "status": "rejected",
                    "code": "SOURCE_IMAGE_PROCESSING_FAILED",
                    "image_error": path_or_code,
                    "message": f"The source image could not be safely processed: {err_msg}"
                },
                img_status="failed",
                err_summary=f"{path_or_code}: {err_msg}"
            )

        featured_image_path = path_or_code
        image_proc_status = "processed"

    # 10. Atomic Post Creation & Final Quota Lock
    saved_file_to_cleanup = featured_image_path
    try:
        with transaction.atomic():
            published_today_final = AutomationPublishLog.objects.select_for_update().filter(
                event_type='published',
                created_at__range=(local_start, local_end)
            ).count()

            if published_today_final >= daily_limit:
                if saved_file_to_cleanup:
                    try:
                        from django.core.files.storage import default_storage
                        default_storage.delete(saved_file_to_cleanup)
                    except Exception:
                        pass
                return log_and_respond(
                    "throttled",
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    {
                        "status": "throttled",
                        "code": "DAILY_PUBLISH_LIMIT_REACHED",
                        "daily_limit": daily_limit,
                        "published_today": published_today_final,
                        "message": "The daily automated publishing limit has been reached."
                    }
                )

            base_slug = slugify(clean_title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            post = BlogPost.objects.create(
                title=clean_title,
                subtitle=clean_subtitle,
                description=clean_description,
                meta_title=clean_meta_title or "",
                meta_description=clean_meta_description or "",
                category=category,
                subcategory=subcategory,
                author=user,
                status="published",
                slug=slug,
                featured_image=featured_image_path,
                image_processing_status=image_proc_status,
                source_name=clean_source_name,
                source_url=src_url,
                source_author=clean_source_author,
                source_published_at=data.get('source_published_at'),
                original_title=clean_original_title,
                original_content_hash=content_hash,
                automation_id=auto_id,
                generated_by_ai=True,
                ai_model=ai_model,
                reviewer_model=reviewer_model,
                review_decision="approved",
                quality_score=quality_score,
                factual_accuracy_score=factual_accuracy_score,
                language_score=language_score,
                seo_score=seo_score,
                review_notes=clean_review_notes or '',
                source_image_url=source_img_url,
                automation_created_at=data.get('automation_created_at'),
            )

            final_tags = list(resolved_tax['reused_tags'])
            for new_spec in resolved_tax['new_tags_to_create']:
                t_obj = get_or_create_tag_safely(new_spec['name'], new_spec['slug'])
                final_tags.append(t_obj)

            post.tags.set(final_tags)
            saved_file_to_cleanup = None

            return log_and_respond(
                "published",
                status.HTTP_201_CREATED,
                {
                    "status": "published",
                    "post_id": post.id,
                    "slug": post.slug,
                    "idempotent_replay": False
                },
                post=post,
                result_code="AUTOMATION_POST_PUBLISHED",
                img_status=image_proc_status
            )

    except Exception as e:
        if saved_file_to_cleanup:
            try:
                from django.core.files.storage import default_storage
                default_storage.delete(saved_file_to_cleanup)
            except Exception:
                pass
        return log_and_respond(
            "processing_failed",
            status.HTTP_400_BAD_REQUEST,
            {
                "status": "error",
                "code": "AUTOMATION_CREATION_FAILED",
                "message": str(e)
            },
            err_summary=str(e)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Per-user token post creation
# ─────────────────────────────────────────────────────────────────────────────

def process_user_token_post_creation(data, user, token_id=None, source_ip=None):
    """
    Handles blog post creation via a personal user API token.

    Key differences from process_automation_post_creation():
      - Uses per-user rate limiting (hourly + daily) keyed by user.id.
      - Simplified gate: only title, description, category_slug are required.
        AI scoring fields (quality_score, review_decision, etc.) are optional.
      - Posts are saved with status='pending' (require admin approval), not
        auto-published, consistent with how regular users submit content.
      - Idempotency via original_content_hash still applies.
      - SSRF-safe image download, HTML sanitization, and taxonomy resolution
        are all reused from the shared service layer.
      - Audit log entries have auth_source='user_token'.
    """
    start_time = time.time()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    raw_src_url = data.get('source_url')
    src_url = normalize_url(raw_src_url) if raw_src_url else None

    raw_hash = data.get('original_content_hash')
    content_hash = (
        clean_text_string(str(raw_hash)).lower()
        if raw_hash is not None and str(raw_hash).strip()
        else None
    )

    raw_source_name = str(data.get('source_name') or '').strip()
    clean_src_name = clean_text_string(raw_source_name) if raw_source_name else None

    def log_and_respond(event_type, http_status, resp_dict, post=None,
                        result_code=None, err_summary='', img_status=None):
        dur_ms = int((time.time() - start_time) * 1000)
        code = result_code or resp_dict.get('code') or resp_dict.get('status')
        record_automation_log(
            event_type=event_type,
            http_status=http_status,
            source_name=clean_src_name,
            source_url=src_url,
            post=post,
            result_code=code,
            duration_ms=dur_ms,
            image_status=img_status,
            error_summary=err_summary or resp_dict.get('message', ''),
            auth_source='user_token',
            token_user=user,
            token_id=token_id,
            source_ip=source_ip,
        )
        return Response(resp_dict, status=http_status)

    # ------------------------------------------------------------------ #
    # 1. Forbidden field check (same as automation)
    # ------------------------------------------------------------------ #
    forbidden_fields = ['author', 'author_id', 'status', 'views', 'is_featured']
    detected_forbidden = [f for f in forbidden_fields if f in data]
    if detected_forbidden:
        return log_and_respond(
            'rejected',
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                'status': 'rejected',
                'code': 'FORBIDDEN_FIELDS',
                'message': f'Payloads must not include internal fields: {", ".join(detected_forbidden)}',
            },
        )

    # ------------------------------------------------------------------ #
    # 2. Idempotency (early exit, same logic)
    # ------------------------------------------------------------------ #
    posts_by_hash = (
        list(BlogPost.objects.filter(original_content_hash=content_hash))
        if content_hash
        else []
    )
    posts_by_url = (
        list(BlogPost.objects.filter(source_url=src_url))
        if src_url
        else []
    )
    all_matched = posts_by_hash + posts_by_url
    matched_ids = set(p.id for p in all_matched)

    if len(matched_ids) > 1:
        return log_and_respond(
            'conflict',
            status.HTTP_409_CONFLICT,
            {
                'status': 'conflict',
                'code': 'IDEMPOTENCY_CONFLICT',
                'message': 'Identifiers resolve to different posts.',
            },
        )

    if len(matched_ids) == 1:
        existing_post = BlogPost.objects.get(id=list(matched_ids)[0])
        return log_and_respond(
            'idempotent_replay',
            status.HTTP_200_OK,
            {
                'status': existing_post.status,
                'post_id': existing_post.id,
                'slug': existing_post.slug,
                'idempotent_replay': True,
            },
            post=existing_post,
            result_code='USER_TOKEN_IDEMPOTENT_REPLAY',
        )

    # ------------------------------------------------------------------ #
    # 3. Per-user hourly rate limit
    # ------------------------------------------------------------------ #
    hourly_limit = getattr(settings, 'TECHLIFE_USER_TOKEN_HOURLY_REQUEST_LIMIT', 20)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_count = AutomationPublishLog.objects.filter(
        token_user=user,
        auth_source='user_token',
        created_at__gte=one_hour_ago,
    ).count()
    if recent_count >= hourly_limit:
        retry_after = 3600  # seconds
        resp = Response(
            {
                'status': 'throttled',
                'code': 'USER_TOKEN_HOURLY_RATE_LIMIT',
                'message': 'Hourly request limit reached for your token.',
                'retry_after_seconds': retry_after,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        resp['Retry-After'] = str(retry_after)
        log_and_respond(
            'throttled',
            status.HTTP_429_TOO_MANY_REQUESTS,
            {
                'status': 'throttled',
                'code': 'USER_TOKEN_HOURLY_RATE_LIMIT',
                'message': 'Hourly request limit reached.',
            },
        )
        return resp

    # ------------------------------------------------------------------ #
    # 4. Per-user daily publish limit (BD timezone)
    # ------------------------------------------------------------------ #
    daily_limit = getattr(settings, 'TECHLIFE_USER_TOKEN_DAILY_POST_LIMIT', 4)
    local_start, local_end = get_asia_dhaka_day_range()

    with transaction.atomic():
        published_today = AutomationPublishLog.objects.select_for_update().filter(
            token_user=user,
            auth_source='user_token',
            event_type='published',
            created_at__range=(local_start, local_end),
        ).count()

        if published_today >= daily_limit:
            resp = Response(
                {
                    'status': 'throttled',
                    'code': 'USER_TOKEN_DAILY_LIMIT_REACHED',
                    'daily_limit': daily_limit,
                    'published_today': published_today,
                    'message': 'Daily post limit reached. Try again tomorrow (BD time).',
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            log_and_respond(
                'throttled',
                status.HTTP_429_TOO_MANY_REQUESTS,
                {'status': 'throttled', 'code': 'USER_TOKEN_DAILY_LIMIT_REACHED',
                 'message': 'Daily limit reached.'},
            )
            return resp

    # ------------------------------------------------------------------ #
    # 5. Simplified gate — only title, description, category_slug required
    # ------------------------------------------------------------------ #
    failed_gates = []
    raw_title = str(data.get('title') or '').strip()
    raw_description = str(data.get('description') or '').strip()
    if not raw_title:
        failed_gates.append('title')
    if not raw_description:
        failed_gates.append('description')
    if not data.get('category_slug', '').strip():
        failed_gates.append('category_slug')

    if failed_gates:
        return log_and_respond(
            'rejected',
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                'status': 'rejected',
                'code': 'REQUIRED_FIELDS_MISSING',
                'failed_gates': failed_gates,
                'message': f'Required fields missing: {", ".join(failed_gates)}',
            },
            err_summary=f'Required fields missing: {", ".join(failed_gates)}',
        )

    # ------------------------------------------------------------------ #
    # 6. Taxonomy resolution (shared)
    # ------------------------------------------------------------------ #
    # For user tokens, tags_list is optional (0 tags is allowed).
    # Inject [] so the shared resolver doesn't reject INVALID_TAGS_LIST,
    # then if error is TOO_FEW_TAGS we resolve category/subcategory directly.
    data_for_taxonomy = dict(data)
    
    # Handle QueryDict arrays from FormData
    if hasattr(data, 'getlist') and 'tags_list' in data:
        data_for_taxonomy['tags_list'] = data.getlist('tags_list')
    elif 'tags_list' not in data_for_taxonomy or data_for_taxonomy['tags_list'] is None:
        data_for_taxonomy['tags_list'] = []

    tax_success, tax_err_code, tax_err_msg, resolved_tax = resolve_automation_taxonomy(data_for_taxonomy)

    # Relax the minimum-tag constraint for user tokens (tags are optional)
    if not tax_success and tax_err_code in ('TOO_FEW_TAGS', 'INVALID_TAGS_LIST'):
        # Tags not provided or too few — resolve category/subcategory directly
        from blog_post.models import Category as _Category, SubCategory as _SubCategory
        from django.utils.text import slugify as _slugify
        _cat_raw = str(data_for_taxonomy.get('category_slug', '')).strip()
        _cat = (
            _Category.objects.filter(slug__iexact=_slugify(_cat_raw)).first()
            or _Category.objects.filter(slug__iexact=_cat_raw).first()
            or _Category.objects.filter(name__iexact=_cat_raw).first()
        )
        if not _cat:
            return log_and_respond(
                'rejected',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {
                    'status': 'rejected',
                    'code': 'TAXONOMY_INVALID',
                    'taxonomy_error': 'UNKNOWN_CATEGORY',
                    'message': f"category_slug '{_cat_raw}' could not be resolved.",
                },
                err_summary=f'UNKNOWN_CATEGORY: {_cat_raw}',
            )
        _sub = None
        _sub_raw = str(data_for_taxonomy.get('subcategory_slug', '') or '').strip()
        if _sub_raw:
            _sub = (
                _SubCategory.objects.filter(slug__iexact=_slugify(_sub_raw), category=_cat).first()
                or _SubCategory.objects.filter(slug__iexact=_sub_raw, category=_cat).first()
            )
        resolved_tax = {
            'category': _cat,
            'subcategory': _sub,
            'reused_tags': [],
            'new_tags_to_create': [],
        }
        tax_success = True


    if not tax_success:
        return log_and_respond(
            'rejected',
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                'status': 'rejected',
                'code': 'TAXONOMY_INVALID',
                'taxonomy_error': tax_err_code,
                'message': tax_err_msg,
            },
            err_summary=f'{tax_err_code}: {tax_err_msg}',
        )

    category = resolved_tax['category']
    subcategory = resolved_tax['subcategory']

    # ------------------------------------------------------------------ #
    # 7. Content sanitization (shared)
    # ------------------------------------------------------------------ #
    san_success, san_err_code, san_err_msg, sanitized_data = sanitize_automation_payload(data)
    if not san_success:
        return log_and_respond(
            'rejected',
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                'status': 'rejected',
                'code': 'CONTENT_INVALID',
                'content_error': san_err_code,
                'message': f'Content could not be safely published: {san_err_msg}',
            },
            err_summary=f'{san_err_code}: {san_err_msg}',
        )

    clean_title = sanitized_data['title']
    clean_description = sanitized_data['description']
    clean_subtitle = sanitized_data.get('subtitle')
    clean_meta_title = sanitized_data.get('meta_title')
    clean_meta_description = sanitized_data.get('meta_description')
    clean_source_name = sanitized_data.get('source_name')
    clean_source_author = sanitized_data.get('source_author')
    clean_original_title = sanitized_data.get('original_title')
    clean_review_notes = sanitized_data.get('review_notes')

    # ------------------------------------------------------------------ #
    # 8. SSRF-safe image download (shared)
    # ------------------------------------------------------------------ #
    raw_img_url = data.get('source_image_url')
    source_img_url = str(raw_img_url).strip() if raw_img_url else None
    featured_image_path = None
    image_proc_status = 'pending'

    if source_img_url:
        temp_slug = slugify(clean_title)
        img_success, path_or_code, err_msg = download_and_localize_automation_image(
            source_img_url, temp_slug, content_hash or 'ut'
        )
        if not img_success:
            return log_and_respond(
                'rejected',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {
                    'status': 'rejected',
                    'code': 'SOURCE_IMAGE_PROCESSING_FAILED',
                    'image_error': path_or_code,
                    'message': f'Source image could not be processed: {err_msg}',
                },
                img_status='failed',
                err_summary=f'{path_or_code}: {err_msg}',
            )
        featured_image_path = path_or_code
        image_proc_status = 'processed'

    # ------------------------------------------------------------------ #
    # 9. Atomic post creation
    # ------------------------------------------------------------------ #
    saved_file_to_cleanup = featured_image_path
    try:
        with transaction.atomic():
            # Final daily-limit re-check under lock
            published_today_final = AutomationPublishLog.objects.select_for_update().filter(
                token_user=user,
                auth_source='user_token',
                event_type='published',
                created_at__range=(local_start, local_end),
            ).count()
            if published_today_final >= daily_limit:
                if saved_file_to_cleanup:
                    try:
                        from django.core.files.storage import default_storage
                        default_storage.delete(saved_file_to_cleanup)
                    except Exception:
                        pass
                return log_and_respond(
                    'throttled',
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    {
                        'status': 'throttled',
                        'code': 'USER_TOKEN_DAILY_LIMIT_REACHED',
                        'message': 'Daily post limit reached.',
                    },
                )

            base_slug = slugify(clean_title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            post = BlogPost.objects.create(
                title=clean_title,
                subtitle=clean_subtitle,
                description=clean_description,
                meta_title=clean_meta_title or '',
                meta_description=clean_meta_description or '',
                category=category,
                subcategory=subcategory,
                author=user,
                status='pending',          # Requires admin approval
                slug=slug,
                featured_image=featured_image_path,
                image_processing_status=image_proc_status,
                source_name=clean_source_name,
                source_url=src_url,
                source_author=clean_source_author,
                source_published_at=data.get('source_published_at'),
                original_title=clean_original_title,
                original_content_hash=content_hash,
                # AI fields are optional for user tokens
                generated_by_ai=bool(data.get('generated_by_ai', False)),
                ai_model=clean_text_string(str(data.get('ai_model') or '')) or None,
                reviewer_model=clean_text_string(str(data.get('reviewer_model') or '')) or None,
                review_notes=clean_review_notes or '',
                source_image_url=source_img_url,
            )

            final_tags = list(resolved_tax['reused_tags'])
            for new_spec in resolved_tax['new_tags_to_create']:
                t_obj = get_or_create_tag_safely(new_spec['name'], new_spec['slug'])
                final_tags.append(t_obj)
            post.tags.set(final_tags)
            saved_file_to_cleanup = None

            return log_and_respond(
                'published',
                status.HTTP_201_CREATED,
                {
                    'status': 'pending',
                    'post_id': post.id,
                    'slug': post.slug,
                    'idempotent_replay': False,
                    'message': 'Post submitted successfully. It will appear after admin review.',
                },
                post=post,
                result_code='USER_TOKEN_POST_SUBMITTED',
                img_status=image_proc_status,
            )

    except Exception as e:
        if saved_file_to_cleanup:
            try:
                from django.core.files.storage import default_storage
                default_storage.delete(saved_file_to_cleanup)
            except Exception:
                pass
        return log_and_respond(
            'processing_failed',
            status.HTTP_400_BAD_REQUEST,
            {
                'status': 'error',
                'code': 'POST_CREATION_FAILED',
                'message': str(e),
            },
            err_summary=str(e),
        )
