from django.core.management.base import BaseCommand
from blog_post.models import HomepageConfig

class Command(BaseCommand):
    help = 'Seed default HomepageConfig entries'

    def handle(self, *args, **kwargs):
        defaults = [
            {'section_key': 'carousel',      'order': 1, 'post_count': 6},
            {'section_key': 'blog_grid',     'order': 2, 'post_count': 8},
            {'section_key': 'latest_news',   'order': 3, 'post_count': 8},
            {'section_key': 'cat_section_1', 'order': 4, 'post_count': 6},
            {'section_key': 'cat_section_2', 'order': 5, 'post_count': 6},
            {'section_key': 'cat_section_3', 'order': 6, 'post_count': 6},
            {'section_key': 'most_viewed',   'order': 7, 'post_count': 8},
        ]
        for d in defaults:
            obj, created = HomepageConfig.objects.get_or_create(
                section_key=d['section_key'], defaults=d
            )
            self.stdout.write(f"{ 'Created' if created else 'Exists' }: {d['section_key']}")
        self.stdout.write(self.style.SUCCESS('Done.'))
from django.core.management.base import BaseCommand

from blog_post.models import HomepageConfig


class Command(BaseCommand):
    help = "Seed default HomepageConfig entries"

    def handle(self, *args, **kwargs):
        defaults = [
            {"section_key": "carousel", "order": 1, "post_count": 6},
            {"section_key": "blog_grid", "order": 2, "post_count": 8},
            {"section_key": "latest_news", "order": 3, "post_count": 8},
            {"section_key": "cat_section_1", "order": 4, "post_count": 6},
            {"section_key": "cat_section_2", "order": 5, "post_count": 6},
            {"section_key": "cat_section_3", "order": 6, "post_count": 6},
            {"section_key": "most_viewed", "order": 7, "post_count": 8},
        ]
        for item in defaults:
            obj, created = HomepageConfig.objects.get_or_create(
                section_key=item["section_key"],
                defaults=item,
            )
            status = "Created" if created else "Already exists"
            self.stdout.write(f"{status}: {item['section_key']}")
        self.stdout.write(self.style.SUCCESS("Done."))
