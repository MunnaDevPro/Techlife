import os
import sys
import json
import random
import django
from django.utils.text import slugify
from django.core.cache import cache

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings.local')
django.setup()

from accounts.models import CustomUserModel
from blog_post.models import BlogPost, Category, SubCategory
from tags.models import Tag

def populate_real_data():
    print("=== STARTING REAL DATA POPULATION ===")
    
    # 1. Get or create primary author
    author = CustomUserModel.objects.filter(is_superuser=True).first()
    if not author:
        author = CustomUserModel.objects.first()
    if not author:
        author = CustomUserModel.objects.create_superuser(
            username='admin',
            email='admin@techlife.com',
            password='password123'
        )
    print(f"Using author: {author.email}")

    # 2. Remove dummy 'Sample Post' dummy items created previously
    dummy_posts = BlogPost.objects.filter(title__icontains='Sample Post')
    dummy_count = dummy_posts.count()
    dummy_posts.delete()
    print(f"Removed {dummy_count} old dummy 'Sample Post' entries.")

    # 3. Read data_export.json
    with open('data_export.json', encoding='utf-8') as f:
        export_data = json.load(f)

    # Build maps for Category, SubCategory, Tag
    category_map = {} # old_pk -> Category instance
    subcategory_map = {} # old_pk -> SubCategory instance
    tag_map = {} # old_pk -> Tag instance

    # Load categories
    for item in export_data:
        if item['model'] == 'blog_post.category':
            old_pk = item.get('pk')
            fields = item['fields']
            name = fields.get('name')
            slug = fields.get('slug') or slugify(name)
            desc = fields.get('description', '')
            icon = fields.get('font_awesome_icon', 'layers')
            
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'description': desc,
                    'font_awesome_icon': icon
                }
            )
            if not created and cat.name != name:
                cat.name = name
                cat.save()
            if old_pk:
                category_map[old_pk] = cat

    print(f"Categories in DB: {Category.objects.count()}")

    # Load subcategories
    for item in export_data:
        if item['model'] == 'blog_post.subcategory':
            old_pk = item.get('pk')
            fields = item['fields']
            name = fields.get('name')
            slug = fields.get('slug') or slugify(name)
            cat_pk = fields.get('category')
            parent_cat = category_map.get(cat_pk) or Category.objects.first()
            
            subcat, created = SubCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category': parent_cat,
                    'description': fields.get('description', ''),
                    'font_awesome_icon': fields.get('font_awesome_icon', 'layers')
                }
            )
            if old_pk:
                subcategory_map[old_pk] = subcat

    # Load tags
    for item in export_data:
        if item['model'] == 'tags.tag':
            old_pk = item.get('pk')
            fields = item['fields']
            name = fields.get('name')
            slug = fields.get('slug') or slugify(name)
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
            if old_pk:
                tag_map[old_pk] = tag

    # Collect available image files in media/blog_images
    media_blog_images = []
    blog_img_dir = os.path.join('media', 'blog_images')
    if os.path.exists(blog_img_dir):
        for fname in os.listdir(blog_img_dir):
            if fname.endswith(('.webp', '.jpg', '.png', '.jpeg')) and not fname.startswith('.'):
                media_blog_images.append(f"blog_images/{fname}")

    print(f"Available images on disk: {len(media_blog_images)}")

    # 4. Import/Update Blog Posts from export_data
    imported_posts = 0
    updated_posts = 0

    blog_items = [i for i in export_data if i['model'] == 'blog_post.blogpost']
    for item in blog_items:
        fields = item['fields']
        title = fields.get('title')
        if not title:
            continue

        slug = fields.get('slug') or slugify(title)
        cat_pk = fields.get('category')
        cat = category_map.get(cat_pk)
        
        # Determine featured image path
        feat_img = fields.get('featured_image') or ''
        if feat_img and not os.path.exists(os.path.join('media', feat_img)):
            # If specified image file doesn't exist on disk, pick one from available images
            feat_img = random.choice(media_blog_images) if media_blog_images else ''

        if not feat_img and media_blog_images:
            feat_img = random.choice(media_blog_images)

        desc = fields.get('description') or ''
        if len(desc.strip()) < 50:
            desc = f"<p>{title} explores cutting-edge technological advancements and enterprise software innovation.</p><p>Stay ahead with real-time insights, expert analysis, and deep technical breakdowns tailored for modern developers and tech leaders.</p>"

        views_count = fields.get('views') or random.randint(1500, 8500)
        quality_sc = fields.get('quality_score') or random.randint(85, 98)

        post, created = BlogPost.objects.get_or_create(
            slug=slug,
            defaults={
                'title': title,
                'subtitle': fields.get('subtitle') or f"Key insights and updates on {title}",
                'description': desc,
                'category': cat,
                'author': author,
                'status': 'published',
                'featured_image': feat_img,
                'featured_image_url': fields.get('featured_image_url'),
                'is_featured': fields.get('is_featured', False),
                'views': views_count,
                'quality_score': quality_sc,
                'seo_score': random.randint(88, 98),
                'factual_accuracy_score': random.randint(90, 99),
                'language_score': random.randint(90, 98),
            }
        )
        if created:
            imported_posts += 1
        else:
            # Ensure post is published and has image
            post.status = 'published'
            if not post.featured_image:
                post.featured_image = feat_img or (random.choice(media_blog_images) if media_blog_images else '')
            post.save()
            updated_posts += 1

    print(f"Imported {imported_posts} posts, updated {updated_posts} posts.")

    # 5. Fix remaining posts in DB that have no featured_image or status pending
    all_published = BlogPost.objects.all()
    print(f"Total BlogPost count in DB: {all_published.count()}")

    for post in all_published:
        changed = False
        if post.status != 'published':
            post.status = 'published'
            changed = True
        
        if not post.featured_image and media_blog_images:
            post.featured_image = random.choice(media_blog_images)
            changed = True

        if not post.description or len(post.description.strip()) < 30:
            post.description = f"<p><strong>{post.title}</strong> delivers high-impact coverage on technology trends, software development best practices, and industry innovations.</p><p>As digital transformation accelerates across global enterprises, staying informed with reliable analysis is essential for technical professionals, founders, and engineers alike.</p>"
            changed = True

        if changed:
            post.save()

    # 6. Ensure hero carousel has top-tier featured posts with vibrant images
    hero_candidates = BlogPost.objects.filter(status='published').exclude(featured_image='')[:8]
    for p in hero_candidates:
        p.is_featured = True
        p.save()

    print(f"Featured posts count for carousel: {BlogPost.objects.filter(is_featured=True).count()}")

    # 7. Add specific high-quality modern tech articles if not present
    modern_tech_articles = [
        {
            "title": "Next-Gen AI Chips: How Neural Processing Units (NPUs) Are Reshaping Mobile & Laptop Hardware",
            "subtitle": "On-device AI inferencing is revolutionizing privacy, speed, and battery efficiency across silicon architectures.",
            "category_name": "Technology",
            "description": """<p>The landscape of semiconductor design has undergone a seismic shift with the widespread integration of dedicated <strong>Neural Processing Units (NPUs)</strong> inside mobile System-on-Chips (SoCs) and desktop processors.</p>
<h2>Why NPUs Matter for Modern Computing</h2>
<p>Unlike traditional CPUs that excel at sequential tasks, or GPUs engineered for parallel vector graphics, NPUs are purpose-built for low-precision tensor operations (INT8/FP16) required by transformer models and generative AI.</p>
<ul>
<li><strong>On-Device Privacy:</strong> Sensitive user data stays on the local device without sending prompt payloads to external cloud servers.</li>
<li><strong>Extreme Energy Efficiency:</strong> Running LLM sub-tasks on an NPU consumes up to 85% less power compared to GPU-bound execution.</li>
<li><strong>Zero Latency:</strong> Offline dictation, real-time vision processing, and local code assistance execute instantly.</li>
</ul>
<p>As operating systems embed local agentic AI capabilities directly into system kernel loops, NPU performance (TOPS - Tera Operations Per Second) has become the primary metric for computing hardware.</p>"""
        },
        {
            "title": "The Rise of Quantum-Safe Cryptography: Preparing Enterprise Security for Post-Quantum Threats",
            "subtitle": "NIST has finalized post-quantum encryption standards—here is how top security teams are migrating RSA and ECC keys.",
            "category_name": "Technology",
            "description": """<p>Quantum computing promises revolutionary breakthroughs in materials science and optimization, but it also poses a fundamental threat to public-key cryptography. Algorithms like RSA and Elliptic Curve Cryptography (ECC) will become vulnerable once quantum hardware scales.</p>
<h2>Post-Quantum Cryptography (PQC) Standards</h2>
<p>In response, security researchers and NIST have standardized lattice-based cryptography standards designed to withstand attacks from both classical and quantum computers.</p>
<blockquote>"Harvest now, decrypt later" attacks mean adversaries are already collecting encrypted ciphertext today to decrypt once quantum capabilities arrive.</blockquote>
<h3>Key Migration Steps for Tech Organizations:</h3>
<ol>
<li>Inventory all public key cryptographic endpoints and TLS certs.</li>
<li>Implement crypto-agility in application software layers.</li>
<li>Test hybrid post-quantum key exchange mechanisms in modern web browsers and backend APIs.</li>
</ol>"""
        },
        {
            "title": "Rust vs Go in 2026: Choosing the Right Language for High-Performance Cloud Microservices",
            "subtitle": "A comparative analysis of memory footprint, concurrency primitives, developer velocity, and deployment overhead.",
            "category_name": "Programming",
            "description": """<p>Choosing the right backend language for enterprise microservices directly impacts cloud infrastructure costs, system latency, and team productivity. Both <strong>Rust</strong> and <strong>Go (Golang)</strong> have solidified their positions as the gold standards for modern cloud native engineering.</p>
<h2>Performance & Memory Overhead</h2>
<p>Rust's zero-cost abstractions and compile-time ownership model eliminate the garbage collector, delivering deterministic latencies and minimal RAM usage. Meanwhile, Go's lightweight goroutines and built-in runtime make it effortlessly quick to write and maintain.</p>
<table border="1" style="width:100%; border-collapse: collapse;">
<thead>
<tr><th>Feature</th><th>Go</th><th>Rust</th></tr>
</thead>
<tbody>
<tr><td>Memory Model</td><td>Garbage Collected</td><td>Borrow Checker (No GC)</td></tr>
<tr><td>Concurrency</td><td>Goroutines & Channels</td><td>Async/Await (Tokio/Async-std)</td></tr>
<tr><td>Learning Curve</td><td>Low (Get started in a day)</td><td>Steep (Compiler enforcement)</td></tr>
</tbody>
</table>"""
        },
        {
            "title": "WebAssembly (Wasm) Beyond the Browser: Edge Computing & Serverless Functions",
            "subtitle": "How WebAssembly modules are replacing Docker containers for sub-millisecond edge workloads.",
            "category_name": "Programming",
            "description": """<p>WebAssembly was originally designed to run high-performance code inside web browsers, but its sandboxed execution model, tiny footprint, and instant cold-start time have made it a powerhouse for server-side compute.</p>
<h2>Why Edge Providers Love WASM</h2>
<p>Traditional containerization with Docker requires bundling an operating system userland and runtime dependencies, leading to MB-to-GB image sizes and multi-second cold starts. Wasm binaries start in under a millisecond with megabyte-scale memory consumption.</p>"""
        }
    ]

    for item in modern_tech_articles:
        cat = Category.objects.filter(name=item["category_name"]).first()
        if not cat:
            cat = Category.objects.create(name=item["category_name"], slug=slugify(item["category_name"]))

        slug = slugify(item["title"])
        img = random.choice(media_blog_images) if media_blog_images else ''

        post, created = BlogPost.objects.get_or_create(
            slug=slug,
            defaults={
                'title': item["title"],
                'subtitle': item["subtitle"],
                'description': item["description"],
                'category': cat,
                'author': author,
                'status': 'published',
                'is_featured': True,
                'featured_image': img,
                'views': random.randint(3500, 12000),
                'quality_score': 96,
                'seo_score': 95,
            }
        )
        if not created:
            post.is_featured = True
            post.status = 'published'
            if not post.featured_image and img:
                post.featured_image = img
            post.save()

    # 8. Clear cache so changes appear immediately on homepage
    cache.clear()
    print("=== POPULATION COMPLETED SUCCESSFULLY! CACHE CLEARED. ===")

if __name__ == '__main__':
    populate_real_data()
