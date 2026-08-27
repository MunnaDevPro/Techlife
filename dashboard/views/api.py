import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from blog_post.models import AutomationPublishLog

@staff_required
def api_docs(request):
    """
    Renders fully functional API Documentation, Instant Preview Sandbox,
    Code Snippets Generator, and Export options.
    """
    ctx = get_dashboard_context(request, "API Documentation & Testbed", "API & Conf", "dashboard:api_docs")
    
    # Define comprehensive endpoint catalogue
    endpoints = [
        {
            "id": "posts_list",
            "category": "Blog Posts",
            "name": "List & Search Blog Posts",
            "method": "GET",
            "path": "/api/blog/posts/",
            "description": "Fetch published blog posts with optional filters for category, subcategory, tag, search query, status, and ordering.",
            "auth_required": "None (Public)",
            "query_params": [
                {"name": "category", "type": "string", "description": "Filter by category slug (e.g. 'tech')"},
                {"name": "subcategory", "type": "string", "description": "Filter by subcategory slug"},
                {"name": "tag", "type": "string", "description": "Filter by tag name"},
                {"name": "search", "type": "string", "description": "Search term for title/subtitle/description"},
                {"name": "is_featured", "type": "boolean", "description": "Filter hero featured posts ('true'/'false')"},
                {"name": "order_by", "type": "string", "description": "Sort field ('-created_at', 'views', '-views', 'title')"}
            ],
            "headers": {
                "Accept": "application/json"
            },
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
            "description": "Retrieve full post details by post slug including additional gallery images and content hash.",
            "auth_required": "None (Public)",
            "path_params": [
                {"name": "slug", "type": "string", "description": "Unique slug identifier of the blog post"}
            ],
            "headers": {
                "Accept": "application/json"
            },
            "sample_response": {
                "id": 101,
                "title": "Artificial Intelligence Innovations in 2026",
                "slug": "artificial-intelligence-innovations-2026",
                "description": "<p>Full content of the post...</p>",
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
            "description": "Ingest and auto-publish automated AI articles. Enforces quality gates, daily limit, SSRF image localization, and content sanitization.",
            "auth_required": "Automation Token (Authorization: Automation <token>)",
            "headers": {
                "Authorization": "Automation <TECHLIFE_AUTOMATION_TOKEN>",
                "Content-Type": "application/json"
            },
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
            "description": "Toggle like status for an authenticated user on a specific post. Supports POST to like and DELETE to unlike.",
            "auth_required": "Session / Basic Auth",
            "headers": {
                "Content-Type": "application/json"
            },
            "sample_response": {
                "status": "liked"
            }
        },
        {
            "id": "posts_record_view",
            "category": "Interactions",
            "name": "Record Post View (IP Tracked)",
            "method": "POST",
            "path": "/api/blog/posts/{slug}/record_view/",
            "description": "Record view counter and unique IP visitor log for a post.",
            "auth_required": "None (Public / Session)",
            "sample_response": {
                "status": "view recorded"
            }
        },
        {
            "id": "categories_list",
            "category": "Taxonomy",
            "name": "List All Categories",
            "method": "GET",
            "path": "/api/blog/categories/",
            "description": "Fetch all blog categories with icon identifiers and descriptions.",
            "auth_required": "None (Public)",
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
            "description": "Fetch subcategories, optionally filtered by parent category.",
            "auth_required": "None (Public)",
            "query_params": [
                {"name": "category", "type": "string", "description": "Parent category slug"}
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
            "description": "Retrieve posts curated for the homepage hero carousel.",
            "auth_required": "None (Public)",
            "sample_response": [
                {
                    "id": 101,
                    "title": "Artificial Intelligence Innovations in 2026",
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
            "description": "Fetch active homepage section ordering and layout configuration.",
            "auth_required": "None (Public)",
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
            new_token = f"techlife_auto_{secrets.token_urlsafe(24)}"
            messages.success(request, f"Generated new automation token recommendation: {new_token}. Update TECHLIFE_AUTOMATION_TOKEN in your environment.")
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
    """
    fmt = request.GET.get("format", "openapi").lower()
    host = request.build_absolute_uri('/')[:-1]

    if fmt == "openapi":
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "TechLife REST API Documentation",
                "description": "Production-ready REST API endpoints for TechLife BD content publishing, taxonomy, and automated AI ingestion.",
                "version": "2.0.0"
            },
            "servers": [{"url": host}],
            "paths": {
                "/api/blog/posts/": {
                    "get": {
                        "summary": "List & Search Blog Posts",
                        "parameters": [
                            {"name": "category", "in": "query", "schema": {"type": "string"}},
                            {"name": "subcategory", "in": "query", "schema": {"type": "string"}},
                            {"name": "search", "in": "query", "schema": {"type": "string"}},
                            {"name": "is_featured", "in": "query", "schema": {"type": "boolean"}}
                        ],
                        "responses": {"200": {"description": "List of published blog posts"}}
                    },
                    "post": {
                        "summary": "Create Automated AI Article",
                        "security": [{"AutomationAuth": []}],
                        "responses": {
                            "201": {"description": "Article published successfully"},
                            "422": {"description": "Policy or gate validation error"}
                        }
                    }
                },
                "/api/blog/categories/": {
                    "get": {
                        "summary": "List Categories",
                        "responses": {"200": {"description": "List of categories"}}
                    }
                },
                "/api/blog/subcategories/": {
                    "get": {
                        "summary": "List Subcategories",
                        "responses": {"200": {"description": "List of subcategories"}}
                    }
                },
                "/api/blog/featured-posts/": {
                    "get": {
                        "summary": "List Featured Posts",
                        "responses": {"200": {"description": "Featured hero posts"}}
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "AutomationAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "Authorization",
                        "description": "Automation token format: 'Automation <TOKEN>'"
                    }
                }
            }
        }
        response = HttpResponse(json.dumps(spec, indent=2), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename="techlife-api-openapi.json"'
        return response

    elif fmt == "postman":
        collection = {
            "info": {
                "name": "TechLife API Collection",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [
                {
                    "name": "Blog Posts",
                    "item": [
                        {
                            "name": "Get Posts List",
                            "request": {
                                "method": "GET",
                                "url": f"{host}/api/blog/posts/"
                            }
                        },
                        {
                            "name": "Publish Automated Post",
                            "request": {
                                "method": "POST",
                                "url": f"{host}/api/blog/posts/",
                                "header": [
                                    {"key": "Authorization", "value": "Automation secret-test-token-12345"},
                                    {"key": "Content-Type", "value": "application/json"}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        response = HttpResponse(json.dumps(collection, indent=2), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename="techlife-api-postman.json"'
        return response

    else:
        # Markdown export
        md_text = f"# TechLife REST API Reference\n\nBase URL: `{host}`\n\n"
        md_text += "## Endpoints\n\n"
        md_text += "### 1. `GET /api/blog/posts/`\nList all published blog posts with filtering.\n\n"
        md_text += "### 2. `POST /api/blog/posts/`\nAutomated ingestion endpoint requiring `Authorization: Automation <token>` header.\n\n"
        md_text += "### 3. `GET /api/blog/categories/`\nGet all category taxonomy items.\n\n"
        md_text += "### 4. `GET /api/blog/featured-posts/`\nGet featured posts.\n\n"
        
        response = HttpResponse(md_text, content_type="text/markdown")
        response['Content-Disposition'] = 'attachment; filename="techlife-api-docs.md"'
        return response
