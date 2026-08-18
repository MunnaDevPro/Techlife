import re
import urllib.parse
from django.db import transaction
from django.utils.text import slugify
from rest_framework.response import Response
from rest_framework import status

from blog_post.models import BlogPost, Category, SubCategory, normalize_url
from blog_post.image_services import download_and_localize_automation_image


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


def process_automation_post_creation(data, user):
    """
    Ingests automation metadata, performs early idempotency checks,
    enforces 12+ strict approval gates, securely downloads and converts
    the source image to a local WebP featured image, and atomically creates published posts.
    """
    # 1. Forbidden Fields Check
    forbidden_fields = ['author', 'author_id', 'status', 'views', 'is_featured']
    detected_forbidden = [f for f in forbidden_fields if f in data]
    if detected_forbidden:
        return Response({
            "status": "rejected",
            "code": "AUTOMATION_FORBIDDEN_FIELDS",
            "message": f"Automation payloads must not specify internal fields: {', '.join(detected_forbidden)}"
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    # 2. Extract Identifiers & Normalize for Idempotency
    raw_auto_id = data.get('automation_id')
    auto_id = str(raw_auto_id).strip() if raw_auto_id is not None and str(raw_auto_id).strip() else None

    raw_src_url = data.get('source_url')
    src_url = normalize_url(raw_src_url) if raw_src_url else None

    raw_hash = data.get('original_content_hash')
    content_hash = str(raw_hash).strip().lower() if raw_hash is not None and str(raw_hash).strip() else None

    # Early Idempotency Search before expensive processing or image downloading
    posts_by_auto_id = list(BlogPost.objects.filter(automation_id=auto_id)) if auto_id else []
    posts_by_url = list(BlogPost.objects.filter(source_url=src_url)) if src_url else []
    posts_by_hash = list(BlogPost.objects.filter(original_content_hash=content_hash)) if content_hash else []

    all_matched = posts_by_auto_id + posts_by_url + posts_by_hash
    matched_ids = set(p.id for p in all_matched)

    if len(matched_ids) > 1:
        return Response({
            "status": "conflict",
            "code": "AUTOMATION_IDEMPOTENCY_CONFLICT",
            "message": "Automation identifiers resolve to different posts."
        }, status=status.HTTP_409_CONFLICT)

    if len(matched_ids) == 1:
        existing_post = BlogPost.objects.get(id=list(matched_ids)[0])
        return Response({
            "status": existing_post.status,
            "post_id": existing_post.id,
            "slug": existing_post.slug,
            "idempotent_replay": True
        }, status=status.HTTP_200_OK)

    # 3. Gate Validation
    failed_gates = []

    # Basic Content Gates
    title = str(data.get('title') or '').strip()
    description = str(data.get('description') or '').strip()

    if not title:
        failed_gates.append('title')
    if not description:
        failed_gates.append('description')

    category_id_or_slug = data.get('category')
    category = None
    if category_id_or_slug:
        if isinstance(category_id_or_slug, int) or (isinstance(category_id_or_slug, str) and category_id_or_slug.isdigit()):
            category = Category.objects.filter(id=int(category_id_or_slug)).first()
        else:
            category = Category.objects.filter(slug=str(category_id_or_slug)).first()
    if not category:
        failed_gates.append('category')

    subcategory_val = data.get('subcategory')
    subcategory = None
    if subcategory_val:
        if isinstance(subcategory_val, int) or (isinstance(subcategory_val, str) and subcategory_val.isdigit()):
            subcategory = SubCategory.objects.filter(id=int(subcategory_val)).first()
        else:
            subcategory = SubCategory.objects.filter(slug=str(subcategory_val)).first()

    # Gate: generated_by_ai
    gen_ai = data.get('generated_by_ai')
    if gen_ai not in [True, 'true', 'True', 1]:
        failed_gates.append('generated_by_ai')

    # Gate: automation_id
    if not auto_id:
        failed_gates.append('automation_id')

    # Gate: source_name
    source_name = str(data.get('source_name') or '').strip()
    if not source_name:
        failed_gates.append('source_name')

    # Gate: source_url
    if not src_url or not is_valid_http_url(src_url):
        failed_gates.append('source_url')

    # Gate: original_content_hash (64-char lowercase SHA-256)
    if not content_hash or not re.match(r'^[a-f0-9]{64}$', content_hash):
        failed_gates.append('original_content_hash')

    # Gate: ai_model & reviewer_model
    ai_model = str(data.get('ai_model') or '').strip()
    if not ai_model:
        failed_gates.append('ai_model')

    reviewer_model = str(data.get('reviewer_model') or '').strip()
    if not reviewer_model:
        failed_gates.append('reviewer_model')

    # Gate: review_decision
    review_decision = str(data.get('review_decision') or '').strip()
    if review_decision != 'approved':
        failed_gates.append('review_decision')

    # Score Gates
    def parse_score(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    quality_score = parse_score(data.get('quality_score'))
    if quality_score is None or quality_score < 90 or quality_score > 100:
        failed_gates.append('quality_score')

    factual_accuracy_score = parse_score(data.get('factual_accuracy_score'))
    if factual_accuracy_score is None or factual_accuracy_score < 95 or factual_accuracy_score > 100:
        failed_gates.append('factual_accuracy_score')

    language_score = parse_score(data.get('language_score'))
    if language_score is None or language_score < 90 or language_score > 100:
        failed_gates.append('language_score')

    seo_score = parse_score(data.get('seo_score'))
    if seo_score is None or seo_score < 80 or seo_score > 100:
        failed_gates.append('seo_score')

    if failed_gates:
        return Response({
            "status": "rejected",
            "code": "AUTOMATION_APPROVAL_FAILED",
            "failed_gates": failed_gates,
            "message": "Article did not satisfy the automated publishing policy."
        }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    # 4. Source Image Download & Localization
    raw_img_url = data.get('source_image_url')
    source_img_url = str(raw_img_url).strip() if raw_img_url else None

    featured_image_path = None
    image_proc_status = "pending"

    if source_img_url:
        temp_slug = slugify(title)
        img_success, path_or_code, err_msg = download_and_localize_automation_image(
            source_img_url, temp_slug, content_hash
        )
        if not img_success:
            return Response({
                "status": "rejected",
                "code": "SOURCE_IMAGE_PROCESSING_FAILED",
                "image_error": path_or_code,
                "message": f"The source image could not be safely processed: {err_msg}"
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        featured_image_path = path_or_code
        image_proc_status = "processed"

    # 5. Atomic Creation with File Cleanup Safety
    saved_file_to_cleanup = featured_image_path
    try:
        with transaction.atomic():
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            post = BlogPost.objects.create(
                title=title,
                subtitle=str(data.get('subtitle') or '').strip() or None,
                description=description,
                category=category,
                subcategory=subcategory,
                author=user,
                status="published",
                slug=slug,
                featured_image=featured_image_path,
                image_processing_status=image_proc_status,
                source_name=source_name,
                source_url=src_url,
                source_author=str(data.get('source_author') or '').strip() or None,
                source_published_at=data.get('source_published_at'),
                original_title=str(data.get('original_title') or '').strip() or None,
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
                review_notes=str(data.get('review_notes') or '').strip(),
                source_image_url=source_img_url,
                automation_created_at=data.get('automation_created_at'),
            )

            # Post created successfully; clear cleanup tracker
            saved_file_to_cleanup = None

            return Response({
                "status": "published",
                "post_id": post.id,
                "slug": post.slug,
                "idempotent_replay": False
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        if saved_file_to_cleanup:
            try:
                from django.core.files.storage import default_storage
                default_storage.delete(saved_file_to_cleanup)
            except Exception:
                pass
        return Response({
            "status": "error",
            "code": "AUTOMATION_CREATION_FAILED",
            "message": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
