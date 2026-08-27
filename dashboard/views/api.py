import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from blog_post.models import AutomationPublishLog


def get_api_endpoints():
    """
    Returns the comprehensive, dynamic API endpoint catalogue.
    Used by both the interactive API Documentation frontend and the Export handlers (OpenAPI, Postman, Markdown).
    """
    token = getattr(settings, "TECHLIFE_AUTOMATION_TOKEN", "secret-test-token-12345")
    return [
        {
            "id": "posts_list",
            "category": "Blog Posts",
            "name": "List & Search Blog Posts",
            "method": "GET",
            "path": "/api/blog/posts/",
            "description": "Fetch published blog posts with optional filters for category, subcategory, tag, search query, status, and ordering.",
            "auth_required": "None (Public)",
            "path_params": [],
            "query_params": [
                {"name": "category", "type": "string", "required": False, "description": "Filter by category slug (e.g. 'technology')"},
                {"name": "subcategory", "type": "string", "required": False, "description": "Filter by subcategory slug (e.g. 'ai')"},
                {"name": "tag", "type": "string", "required": False, "description": "Filter by tag slug or name"},
                {"name": "search", "type": "string", "required": False, "description": "Search keyword matching title, subtitle, or content"},
                {"name": "is_featured", "type": "boolean", "required": False, "description": "Filter hero featured posts ('true' / 'false')"},
                {"name": "order_by", "type": "string", "required": False, "description": "Sort order ('-created_at', 'views', '-views', 'title')"}
            ],
            "body_params": [],
            "headers": {
                "Accept": "application/json"
            },
            "rules": [
                "Publicly accessible read-only endpoint.",
                "Returns paginated results matching DRF Standard Pagination format.",
                "Default sorting is by newest created date (-created_at)."
            ],
            "sample_response": {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": 101,
                        "title": "Artificial Intelligence Innovations in 2026",
                        "subtitle": "A deep dive into multi-modal models",
                        "slug": "artificial-intelligence-innovations-2026",
                        "description": "<p>Detailed breakdown of AI breakthroughs...</p>",
                        "featured_image": "/media/blog_images/hero.webp",
                        "featured_image_url": "https://techlife.com.bd/media/blog_images/hero.webp",
                        "category": {"id": 1, "name": "Technology", "slug": "technology", "font_awesome_icon": "cpu"},
                        "subcategory": {"id": 4, "name": "Artificial Intelligence", "slug": "ai", "font_awesome_icon": "brain"},
                        "author": {"id": 2, "username": "techlife_desk", "email": "techlife_desk@techlifebd.com", "first_name": "TechLife", "last_name": "Desk"},
                        "status": "published",
                        "is_featured": True,
                        "views": 1540,
                        "likes_count": 42,
                        "content_quality": 95,
                        "created_at": "2026-08-27T10:00:00Z",
                        "updated_at": "2026-08-27T10:05:00Z",
                        "tags": [{"id": 5, "name": "ai", "slug": "ai"}],
                        "comments_count": 12
                    }
                ]
            }
        },
        {
            "id": "posts_detail",
            "category": "Blog Posts",
            "name": "Get Blog Post Details",
            "method": "GET",
            "path": "/api/blog/posts/{slug}/",
            "description": "Retrieve complete post details by post slug including full content, additional gallery images, author metadata, and content hash.",
            "auth_required": "None (Public)",
            "path_params": [
                {"name": "slug", "type": "string", "required": True, "description": "Unique slug identifier of the target blog post"}
            ],
            "query_params": [],
            "body_params": [],
            "headers": {
                "Accept": "application/json"
            },
            "rules": [
                "Public read-only endpoint.",
                "Returns 404 Not Found if post slug does not exist or is in draft/archived status."
            ],
            "sample_response": {
                "id": 101,
                "title": "Artificial Intelligence Innovations in 2026",
                "slug": "artificial-intelligence-innovations-2026",
                "description": "<p>Full HTML content of the post...</p>",
                "additional_images": [],
                "content_hash": "e10adc3949ba59abbe56e057f20f883e",
                "image_hash": "c33367701511b4f6020ec61ded352059"
            }
        },
        {
            "id": "posts_create_automation",
            "category": "Automation Ingestion",
            "name": "Create Automated Post",
            "method": "POST",
            "path": "/api/blog/posts/",
            "description": "Ingest and auto-publish automated AI articles. Enforces system quality gates, daily rate limits, SSRF image localization, and content sanitization.",
            "auth_required": f"Automation Token (Authorization: Automation {token})",
            "path_params": [],
            "query_params": [],
            "headers": {
                "Authorization": f"Automation {token}",
                "Content-Type": "application/json"
            },
            "body_params": [
                {"name": "title", "type": "string", "required": True, "description": "Title of the post (max 255 characters)"},
                {"name": "description", "type": "string", "required": True, "description": "HTML body content of the article"},
                {"name": "category_slug", "type": "string", "required": True, "description": "Slug of the primary category (e.g. 'technology')"},
                {"name": "subcategory_slug", "type": "string", "required": False, "description": "Slug of the subcategory (e.g. 'ai')"},
                {"name": "tags_list", "type": "array of strings", "required": False, "description": "List of tag names (e.g. ['quantum', 'tech'])"},
                {"name": "source_name", "type": "string", "required": False, "description": "Original publisher/source name (e.g. 'TechCrunch')"},
                {"name": "source_url", "type": "url", "required": False, "description": "Original source article link"},
                {"name": "source_image_url", "type": "url", "required": False, "description": "Remote image URL to fetch and convert to WebP locally"},
                {"name": "original_content_hash", "type": "string (sha256)", "required": False, "description": "Unique SHA256 content hash for idempotent deduplication"},
                {"name": "automation_id", "type": "string", "required": False, "description": "Workflow execution ID from n8n or Python automation runner"},
                {"name": "generated_by_ai", "type": "boolean", "required": False, "description": "Flag marking article as AI-generated (default: True)"},
                {"name": "ai_model", "type": "string", "required": False, "description": "Generator AI model identifier (e.g. 'gpt-4o')"},
                {"name": "reviewer_model", "type": "string", "required": False, "description": "Reviewer AI model identifier (e.g. 'claude-3-5-sonnet')"},
                {"name": "review_decision", "type": "string", "required": False, "description": "AI review verdict ('approved' | 'rejected')"},
                {"name": "quality_score", "type": "integer (1-100)", "required": False, "description": "Overall quality rating (minimum 80 required for auto-publish)"},
                {"name": "factual_accuracy_score", "type": "integer (1-100)", "required": False, "description": "Factual accuracy assessment score"},
                {"name": "seo_score", "type": "integer (1-100)", "required": False, "description": "SEO optimization score"}
            ],
            "rules": [
                "Mandatory Header: 'Authorization: Automation <TOKEN>'",
                "Rate Limit: Hourly limit of 20 requests and daily limit of 4 published posts.",
                "Quality Gate: Post must meet minimum quality score (80+) or request returns HTTP 422.",
                "Idempotency: Re-submitting an existing original_content_hash returns HTTP 200 with idempotent_replay=True without duplicating.",
                "SSRF Protection: Remote featured images are validated, safely downloaded, and stored locally as WebP."
            ],
            "sample_request": {
                "title": "n8n Automated Tech News Article",
                "description": "<h2>Next-Gen Quantum Computing</h2><p>Comprehensive article body with high factual accuracy...</p>",
                "category_slug": "technology",
                "tags_list": ["quantum", "tech", "computing"],
                "source_name": "TechCrunch",
                "source_url": "https://techcrunch.com/2026/quantum-breakthrough",
                "source_image_url": "https://images.techcrunch.com/quantum.jpg",
                "original_content_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
                "automation_id": "n8n_exec_20260827_001",
                "generated_by_ai": True,
                "ai_model": "gpt-4o",
                "reviewer_model": "claude-3-5-sonnet",
                "review_decision": "approved",
                "quality_score": 94,
                "factual_accuracy_score": 98,
                "language_score": 93,
                "seo_score": 86
            },
            "sample_response": {
                "status": "published",
                "post_id": 102,
                "slug": "n8n-automated-tech-news-article",
                "idempotent_replay": False
            }
        },
        {
            "id": "posts_like",
            "category": "Interactions",
            "name": "Like / Unlike Post",
            "method": "POST",
            "path": "/api/blog/posts/{slug}/like/",
            "description": "Toggle like status for a user or visitor session on a post. Supports POST to like and DELETE to remove a like.",
            "auth_required": "Session / Cookie / User Auth",
            "path_params": [
                {"name": "slug", "type": "string", "required": True, "description": "Unique slug identifier of post to like or unlike"}
            ],
            "query_params": [],
            "body_params": [],
            "headers": {
                "Content-Type": "application/json",
                "X-CSRFToken": "<CSRF_TOKEN>"
            },
            "rules": [
                "Sending POST adds a like to the target post and increments likes_count.",
                "Sending DELETE unlikes the post and decrements likes_count.",
                "Prevents duplicate likes: Authenticated users are tracked by User ID; anonymous visitors are tracked by IP/Session Key.",
                "Returns updated likes_count and user_has_liked status flag."
            ],
            "sample_response": {
                "status": "liked",
                "likes_count": 43,
                "user_has_liked": True
            }
        },
        {
            "id": "posts_record_view",
            "category": "Interactions",
            "name": "Record Post View (IP Tracked)",
            "method": "POST",
            "path": "/api/blog/posts/{slug}/record_view/",
            "description": "Log post view event and record visitor IP analytics.",
            "auth_required": "None (Public / Session)",
            "path_params": [
                {"name": "slug", "type": "string", "required": True, "description": "Unique slug identifier of the target post"}
            ],
            "query_params": [],
            "body_params": [],
            "headers": {
                "Content-Type": "application/json"
            },
            "rules": [
                "Increments view counter for the target post.",
                "Tracks visitor IP address in audit log for unique traffic analytics.",
                "Prevents artificially inflated views by rate-limiting repeat view triggers per IP window."
            ],
            "sample_response": {
                "status": "view recorded",
                "views": 1541
            }
        },
        {
            "id": "categories_list",
            "category": "Taxonomy",
            "name": "List All Categories",
            "method": "GET",
            "path": "/api/blog/categories/",
            "description": "Fetch all main blog categories with icon identifiers, post counts, and descriptions.",
            "auth_required": "None (Public)",
            "path_params": [],
            "query_params": [],
            "body_params": [],
            "headers": {
                "Accept": "application/json"
            },
            "rules": [
                "Public read-only endpoint.",
                "Returns active categories sorted alphabetically by name."
            ],
            "sample_response": [
                {
                    "id": 1,
                    "name": "Technology",
                    "slug": "technology",
                    "font_awesome_icon": "cpu",
                    "description": "Tech news, AI, hardware, software",
                    "created_at": "2026-08-01T00:00:00Z"
                }
            ]
        },
        {
            "id": "subcategories_list",
            "category": "Taxonomy",
            "name": "List Subcategories",
            "method": "GET",
            "path": "/api/blog/subcategories/",
            "description": "Fetch subcategories, optionally filtered by parent category slug.",
            "auth_required": "None (Public)",
            "path_params": [],
            "query_params": [
                {"name": "category", "type": "string", "required": False, "description": "Parent category slug (e.g. 'technology')"}
            ],
            "body_params": [],
            "headers": {
                "Accept": "application/json"
            },
            "rules": [
                "Public read-only endpoint."
            ],
            "sample_response": [
                {
                    "id": 4,
                    "name": "Artificial Intelligence",
                    "slug": "ai",
                    "description": "AI models, LLMs, robotics",
                    "category": 1,
                    "category_name": "Technology"
                }
            ]
        },
        {
            "id": "featured_posts",
            "category": "Curated Collections",
            "name": "Get Featured Hero Posts",
            "method": "GET",
            "path": "/api/blog/featured-posts/",
            "description": "Retrieve posts curated for the homepage hero carousel and top featured spots.",
            "auth_required": "None (Public)",
            "path_params": [],
            "query_params": [
                {"name": "limit", "type": "integer", "required": False, "description": "Maximum posts to return (default 5)"}
            ],
            "body_params": [],
            "headers": {
                "Accept": "application/json"
            },
            "rules": [
                "Public read-only endpoint.",
                "Only returns published posts marked as is_featured=True."
            ],
            "sample_response": [
                {
                    "id": 101,
                    "title": "Artificial Intelligence Innovations in 2026",
                    "slug": "artificial-intelligence-innovations-2026",
                    "is_featured": True
                }
            ]
        },
        {
            "id": "homepage_configs",
            "category": "Site Settings",
            "name": "Get Homepage Layout Configs",
            "method": "GET",
            "path": "/api/blog/homepage-configs/",
            "description": "Fetch active homepage section ordering and layout configurations.",
            "auth_required": "None (Public)",
            "path_params": [],
            "query_params": [],
            "body_params": [],
            "headers": {
                "Accept": "application/json"
            },
            "rules": [
                "Public read-only endpoint.",
                "Returns ordered list of active homepage layout sections."
            ],
            "sample_response": [
                {
                    "id": 1,
                    "section_key": "carousel",
                    "title": "Hero Carousel",
                    "post_count": 5,
                    "is_active": True,
                    "order": 1
                }
            ]
        }
    ]


@staff_required
def api_docs(request):
    """
    Renders fully functional API Documentation, Instant Preview Sandbox,
    Code Snippets Generator, and Export options.
    """
    ctx = get_dashboard_context(request, "API Documentation & Testbed", "API & Conf", "dashboard:api_docs")
    endpoints = get_api_endpoints()
    ctx["endpoints_json"] = json.dumps(endpoints)
    ctx["endpoints"] = endpoints
    return render(request, "dashboard/api_docs.html", ctx)


@staff_required
def api_config(request):
    """
    API Configuration & Automation Token Management view.
    """
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "regenerate_token":
            import secrets
            import os
            
            new_token = f"techlife_auto_{secrets.token_urlsafe(24)}"
            
            env_path = os.path.join(settings.BASE_DIR, '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
                
            token_found = False
            for i, line in enumerate(lines):
                if line.startswith('TECHLIFE_AUTOMATION_TOKEN='):
                    lines[i] = f'TECHLIFE_AUTOMATION_TOKEN={new_token}\n'
                    token_found = True
                    break
                    
            if not token_found:
                if lines and not lines[-1].endswith('\n'):
                    lines.append('\n')
                lines.append(f'TECHLIFE_AUTOMATION_TOKEN={new_token}\n')
                
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
            settings.TECHLIFE_AUTOMATION_TOKEN = new_token
            
            messages.success(request, f"Generated and saved new automation token! Your .env file has been updated successfully.")
        return redirect("dashboard:api_config")

    token = getattr(settings, "TECHLIFE_AUTOMATION_TOKEN", "secret-test-token-12345")
    enabled = getattr(settings, "TECHLIFE_AUTOMATION_ENABLED", True)
    author_username = getattr(settings, "TECHLIFE_AUTOMATION_AUTHOR_USERNAME", "techlife_desk")
    hourly_limit = getattr(settings, "TECHLIFE_AUTOMATION_HOURLY_REQUEST_LIMIT", 20)
    daily_limit = getattr(settings, "TECHLIFE_AUTOMATION_DAILY_POST_LIMIT", 4)
    
    recent_logs = AutomationPublishLog.objects.all().order_by("-created_at")[:25]
    total_logs_count = AutomationPublishLog.objects.count()

    ctx = get_dashboard_context(request, "API Tokens & Configuration", "API & Conf", "dashboard:api_config")
    ctx.update({
        "automation_token": token,
        "automation_enabled": enabled,
        "author_username": author_username,
        "hourly_limit": hourly_limit,
        "daily_limit": daily_limit,
        "recent_logs": recent_logs,
        "total_logs_count": total_logs_count,
    })
    return render(request, "dashboard/api_config.html", ctx)


@staff_required
def api_export(request):
    """
    Export API Documentation as OpenAPI 3.0 specification, Postman Collection JSON, or Markdown document.
    Dynamically generates full specification from the complete endpoint catalog.
    """
    fmt = request.GET.get("format", "openapi").lower()
    host = request.build_absolute_uri('/')[:-1]
    endpoints = get_api_endpoints()

    if fmt == "openapi":
        paths = {}
        for ep in endpoints:
            path_key = ep["path"]
            method_key = ep["method"].lower()
            if path_key not in paths:
                paths[path_key] = {}
            
            parameters = []
            for pp in ep.get("path_params", []):
                parameters.append({
                    "name": pp["name"],
                    "in": "path",
                    "required": True,
                    "schema": {"type": pp.get("type", "string")},
                    "description": pp.get("description", "")
                })
            for qp in ep.get("query_params", []):
                parameters.append({
                    "name": qp["name"],
                    "in": "query",
                    "required": qp.get("required", False),
                    "schema": {"type": qp.get("type", "string")},
                    "description": qp.get("description", "")
                })

            op_spec = {
                "summary": ep["name"],
                "description": ep["description"] + ("\n\n**Rules:**\n- " + "\n- ".join(ep.get("rules", [])) if ep.get("rules") else ""),
                "parameters": parameters,
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "content": {
                            "application/json": {
                                "example": ep.get("sample_response", {})
                            }
                        }
                    }
                }
            }

            if ep.get("body_params"):
                properties = {}
                required_props = []
                for bp in ep["body_params"]:
                    prop_type = "string"
                    if "array" in bp.get("type", ""):
                        prop_type = "array"
                    elif "boolean" in bp.get("type", ""):
                        prop_type = "boolean"
                    elif "integer" in bp.get("type", ""):
                        prop_type = "integer"

                    properties[bp["name"]] = {
                        "type": prop_type,
                        "description": bp.get("description", "")
                    }
                    if bp.get("required"):
                        required_props.append(bp["name"])

                op_spec["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": properties,
                                "required": required_props
                            },
                            "example": ep.get("sample_request", {})
                        }
                    }
                }

            if "Automation" in ep.get("auth_required", ""):
                op_spec["security"] = [{"AutomationAuth": []}]

            paths[path_key][method_key] = op_spec

        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "TechLife REST API Specifications",
                "description": "Complete production REST API specs for TechLife BD content publishing, taxonomy, interactions, and automated AI ingestion.",
                "version": "2.0.0"
            },
            "servers": [{"url": host}],
            "paths": paths,
            "components": {
                "securitySchemes": {
                    "AutomationAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "Authorization",
                        "description": "Automation token header format: 'Automation <TOKEN>'"
                    }
                }
            }
        }
        response = HttpResponse(json.dumps(spec, indent=2), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename="techlife-api-openapi.json"'
        return response

    elif fmt == "postman":
        categories = {}
        for ep in endpoints:
            cat = ep["category"]
            if cat not in categories:
                categories[cat] = []
            
            headers = []
            for k, v in ep.get("headers", {}).items():
                headers.append({"key": k, "value": v})

            pm_item = {
                "name": ep["name"],
                "request": {
                    "method": ep["method"],
                    "header": headers,
                    "url": {
                        "raw": f"{host}{ep['path']}",
                        "host": [host],
                        "path": [p for p in ep['path'].split('/') if p]
                    },
                    "description": ep["description"]
                }
            }
            if ep.get("sample_request") and ep["method"] != "GET":
                pm_item["request"]["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(ep["sample_request"], indent=2),
                    "options": {"raw": {"language": "json"}}
                }
            categories[cat].append(pm_item)

        items = []
        for cat_name, cat_items in categories.items():
            items.append({
                "name": cat_name,
                "item": cat_items
            })

        collection = {
            "info": {
                "name": "TechLife Complete REST API Collection",
                "description": "Comprehensive Postman Collection for all TechLife API endpoints.",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": items
        }
        response = HttpResponse(json.dumps(collection, indent=2), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename="techlife-api-postman.json"'
        return response

    else:
        # Markdown export
        md_text = f"# TechLife REST API Complete Reference\n\nBase URL: `{host}`\n\n"
        for idx, ep in enumerate(endpoints, 1):
            md_text += f"## {idx}. {ep['name']} (`{ep['method']} {ep['path']}`)\n\n"
            md_text += f"**Category:** {ep['category']}  \n"
            md_text += f"**Authentication:** `{ep['auth_required']}`  \n\n"
            md_text += f"{ep['description']}\n\n"
            
            if ep.get("rules"):
                md_text += "### Rules & Constraints\n"
                for rule in ep["rules"]:
                    md_text += f"- {rule}\n"
                md_text += "\n"

            if ep.get("path_params"):
                md_text += "### Path Parameters\n| Parameter | Type | Required | Description |\n|---|---|---|---|\n"
                for pp in ep["path_params"]:
                    md_text += f"| `{pp['name']}` | `{pp['type']}` | Yes | {pp['description']} |\n"
                md_text += "\n"

            if ep.get("query_params"):
                md_text += "### Query Parameters\n| Parameter | Type | Required | Description |\n|---|---|---|---|\n"
                for qp in ep["query_params"]:
                    req_str = "Yes" if qp.get("required") else "No"
                    md_text += f"| `{qp['name']}` | `{qp['type']}` | {req_str} | {qp['description']} |\n"
                md_text += "\n"

            if ep.get("body_params"):
                md_text += "### Request Body Fields (JSON)\n| Field | Type | Required | Description |\n|---|---|---|---|\n"
                for bp in ep["body_params"]:
                    req_str = "Yes" if bp.get("required") else "No"
                    md_text += f"| `{bp['name']}` | `{bp['type']}` | {req_str} | {bp['description']} |\n"
                md_text += "\n"

            if ep.get("sample_request"):
                md_text += "### Sample Request\n```json\n" + json.dumps(ep["sample_request"], indent=2) + "\n```\n\n"

            if ep.get("sample_response"):
                md_text += "### Sample Response\n```json\n" + json.dumps(ep["sample_response"], indent=2) + "\n```\n\n"

            md_text += "---\n\n"

        response = HttpResponse(md_text, content_type="text/markdown")
        response['Content-Disposition'] = 'attachment; filename="techlife-api-reference.md"'
        return response
