import os
import sys
import django
from django.utils.text import slugify
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Techlife.settings')
django.setup()

from accounts.models import CustomUserModel
from blog_post.models import BlogPost, Category

def create_dummy_companies():
    fake = Faker()
    
    # Get an author (usually first superuser)
    author = CustomUserModel.objects.filter(is_superuser=True).first()
    if not author:
        author = CustomUserModel.objects.first()
        if not author:
            print("No users found in database to act as author!")
            return
            
    print(f"Using author: {author.email}")
    
    # Get or create a category
    category, created = Category.objects.get_or_create(
        name="Technology Companies",
        defaults={'slug': 'technology-companies', 'description': 'Companies operating in the tech sector.'}
    )
    
    companies_data = [
        {
            "title": "Quantum Solutions Inc.",
            "subtitle": "Pioneering the future of quantum computing.",
            "company_email": "hello@quantumsolutions.example.com",
            "company_phone": "+1-555-0100"
        },
        {
            "title": "Nexus Dynamics",
            "subtitle": "Global leader in supply chain automation.",
            "company_email": "contact@nexusdynamics.example.com",
            "company_phone": "+1-555-0199"
        },
        {
            "title": "EcoTech Innovations",
            "subtitle": "Sustainable energy management software.",
            "company_email": "green@ecotechinnovations.example.com",
            "company_phone": "+1-555-0123"
        },
        {
            "title": "Synapse Neural Networks",
            "subtitle": "Advanced AI models for healthcare.",
            "company_email": "ai@synapsehealth.example.com",
            "company_phone": "+1-555-0144"
        },
        {
            "title": "AeroSpace Logistics",
            "subtitle": "Next-generation drone delivery systems.",
            "company_email": "flight@aerospacelogistics.example.com",
            "company_phone": "+1-555-0177"
        },
        {
            "title": "CyberShield Security",
            "subtitle": "Enterprise-grade threat protection.",
            "company_email": "secure@cybershield.example.com",
            "company_phone": "+1-555-0188"
        }
    ]
    
    count = 0
    for data in companies_data:
        title = data["title"]
        slug = slugify(title)
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        post, created = BlogPost.objects.get_or_create(
            title=title,
            defaults={
                'subtitle': data["subtitle"],
                'slug': slug,
                'company_email': data["company_email"],
                'company_phone': data["company_phone"],
                'description': fake.paragraphs(nb=3),
                'is_company': True,
                'status': 'published',
                'author': author,
                'category': category,
            }
        )
        if created:
            count += 1
            print(f"Created company: {title}")
        else:
            print(f"Company already exists: {title}")
            
    print(f"Successfully added {count} dummy companies!")

if __name__ == '__main__':
    create_dummy_companies()
