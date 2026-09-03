import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings.local')
django.setup()

from blog_post.models import Category, SubCategory

company_categories_data = {
    "Software & Technology": [
        "Web & App Development",
        "Cloud & IT Services",
        "Cybersecurity & Data Safety",
        "AI & Machine Learning",
        "SaaS & Enterprise Software"
    ],
    "E-Commerce & Retail": [
        "Online Marketplace & Stores",
        "Fashion & Apparel",
        "Consumer Electronics",
        "Grocery & Food Delivery"
    ],
    "Healthcare & Medical": [
        "Hospitals & Specialized Clinics",
        "Telemedicine & Home Care",
        "Pharmaceuticals & Medical Devices",
        "Diagnostic & Pathology Labs"
    ],
    "Construction & Real Estate": [
        "Real Estate Agency & Property",
        "Architecture & Interior Design",
        "Building & Commercial Construction",
        "Civil Engineering & Contracting"
    ],
    "Finance & Professional Services": [
        "Banking & Fintech",
        "Accounting, Audit & Tax",
        "Legal & Compliance Services",
        "Investment & Asset Management"
    ],
    "Marketing & Advertising": [
        "Digital Marketing & SEO",
        "Branding, PR & Communications",
        "Media & Video Production",
        "Event Management & Promotion"
    ],
    "Manufacturing & Industrial": [
        "Garments & Textile Industry",
        "Industrial Machinery & Tools",
        "Packaging & Chemical Products",
        "Electronics & Hardware Manufacturing"
    ],
    "Education & Training": [
        "Online E-Learning & EdTech",
        "Professional Training Institutes",
        "Schools, Colleges & Universities",
        "Study Abroad & Student Consultancy"
    ],
    "Travel & Hospitality": [
        "Hotels, Resorts & Homestays",
        "Travel Agency & Tour Operators",
        "Restaurants, Cafes & Catering",
        "Transport & Car Rentals"
    ],
    "Business & Consulting": [
        "Management & Strategy Consulting",
        "HR, Recruitment & Staffing",
        "Logistics & Freight Forwarding",
        "Security & Facility Management"
    ]
}

# Existing categories that should be marked as company categories
existing_company_names = ["Technology Companies", "Healthcare at Home", "Specialized Design Services", "Home Painting"]
Category.objects.filter(name__in=existing_company_names).update(is_company_category=True)

for cat_name, subcats in company_categories_data.items():
    cat_obj, created = Category.objects.get_or_create(
        name=cat_name,
        defaults={"is_company_category": True, "font_awesome_icon": "briefcase"}
    )
    if not cat_obj.is_company_category:
        cat_obj.is_company_category = True
        cat_obj.save()
        
    for sub_name in subcats:
        SubCategory.objects.get_or_create(
            category=cat_obj,
            name=sub_name
        )

print("Successfully seeded industry categories!")
