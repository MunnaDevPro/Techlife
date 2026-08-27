import os
import django
import urllib.request
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings.local')
django.setup()

from blog_post.models import BlogPost, Category
from accounts.models import CustomUserModel

def seed():
    # Get or create a superuser for author
    author = CustomUserModel.objects.first()
    if not author:
        author = CustomUserModel.objects.create_superuser('admin', 'admin@example.com', 'password')

    categories = Category.objects.all()
    if not categories:
        print("No categories found. Creating some...")
        for name in ['News', 'Technology', 'Lifestyle', 'Programming', 'Health', 'Travel']:
            Category.objects.get_or_create(name=name)
        categories = Category.objects.all()

    for category in categories:
        print(f"Creating posts for category: {category.name}")
        for i in range(1, 6): # 5 posts per category
            title = f"Sample Post {i} about {category.name}"
            # Check if post exists to avoid duplicates
            if BlogPost.objects.filter(title=title).exists():
                print(f"  Post '{title}' already exists. Skipping.")
                continue
                
            post = BlogPost(
                title=title,
                description=f"<p>This is the amazing content for {title}. Here we discuss the intricacies of {category.name} and explore new frontiers.</p>",
                category=category,
                author=author,
                status='published'
            )
            
            # Download a random image
            image_url = f"https://picsum.photos/800/600?random={category.id * 10 + i}"
            print(f"  Downloading image from {image_url}...")
            try:
                response = urllib.request.urlopen(image_url)
                if response.status == 200:
                    image_content = response.read()
                    post.featured_image.save(f'sample_{category.slug}_{i}.jpg', ContentFile(image_content), save=False)
            except Exception as e:
                print(f"  Failed to download image: {e}")
                
            post.save()
            print(f"  Created post: {title}")

if __name__ == '__main__':
    seed()
    print("Seeding complete!")
