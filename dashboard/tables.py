import django_tables2 as tables
from blog_post.models import BlogPost
from django.utils.html import format_html

class BlogPostTable(tables.Table):
    selection = tables.CheckBoxColumn(
        accessor='pk',
        attrs={
            "th__input": {"class": "rounded border-gray-300 text-blue-600 focus:ring-blue-500", "id": "select-all-posts"},
            "td__input": {"class": "post-select rounded border-gray-300 text-blue-600 focus:ring-blue-500"}
        },
        orderable=False
    )
    
    thumbnail = tables.Column(empty_values=(), orderable=False)
    title = tables.Column(attrs={"td": {"class": "font-medium text-gray-900"}})
    author = tables.Column(accessor='author.email')
    category = tables.Column(accessor='category.name')
    status = tables.Column()
    views = tables.Column()
    created_at = tables.DateTimeColumn(format='Y-m-d H:i', verbose_name="Created Date")
    actions = tables.Column(empty_values=(), orderable=False, verbose_name="Actions")

    class Meta:
        model = BlogPost
        fields = ("selection", "thumbnail", "title", "author", "category", "status", "views", "created_at", "actions")
        attrs = {"class": "min-w-full divide-y divide-gray-200 text-[14px] text-left"}

    def render_thumbnail(self, record):
        if record.featured_image:
            return format_html('<img src="{}" class="w-10 h-10 object-cover rounded-md border border-gray-200">', record.featured_image.url)
        elif record.featured_image_url:
            return format_html('<img src="{}" class="w-10 h-10 object-cover rounded-md border border-gray-200">', record.featured_image_url)
        return format_html('<div class="w-10 h-10 bg-gray-100 rounded-md border border-gray-200 flex items-center justify-center text-gray-400"><i data-lucide="image" class="w-5 h-5"></i></div>')

    def render_status(self, value):
        badge_type = "info"
        if value == "published":
            badge_type = "success"
        elif value in ["pending", "edited"]:
            badge_type = "warning"
        elif value == "rejected":
            badge_type = "danger"
            
        bg_cls = f"bg-{badge_type}-50 text-{badge_type}-700 border border-{badge_type}-200"
        if badge_type == "warning":
            bg_cls = "bg-yellow-50 text-yellow-700 border border-yellow-200"
            
        return format_html(
            '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium {}">{}</span>',
            bg_cls,
            value.capitalize()
        )

    def render_actions(self, record):
        edit_url = f"/dashboard/content/posts/{record.pk}/edit/"
        view_url = f"/details/{record.slug}/"
        
        approve_btn = ""
        reject_btn = ""
        if record.status in ["pending", "edited"]:
            approve_btn = format_html(
                '<button hx-post="/dashboard/content/posts/{}/approve/" hx-target="#main-content" class="w-full text-left px-4 py-2 text-[14px] text-green-600 hover:bg-green-50 flex items-center gap-2"><i data-lucide="check" class="w-4 h-4"></i> Approve</button>',
                record.pk
            )
            reject_btn = format_html(
                '<button hx-post="/dashboard/content/posts/{}/reject/" hx-target="#main-content" class="w-full text-left px-4 py-2 text-[14px] text-yellow-600 hover:bg-yellow-50 flex items-center gap-2"><i data-lucide="x" class="w-4 h-4"></i> Reject</button>',
                record.pk
            )

        delete_btn = format_html(
            '<button @click="confirmDeleteId = {}; showDeleteModal = true" class="w-full text-left px-4 py-2 text-[14px] text-red-600 hover:bg-red-50 flex items-center gap-2"><i data-lucide="trash-2" class="w-4 h-4"></i> Delete</button>',
            record.pk
        )

        return format_html(
            '<div x-data="{{ open: false }}" class="relative inline-block text-left">'
            '  <button @click="open = !open" class="p-1 rounded hover:bg-gray-100 text-gray-500">'
            '    <i data-lucide="more-horizontal" class="w-5 h-5"></i>'
            '  </button>'
            '  <div x-show="open" @click.outside="open = false" class="origin-top-right absolute right-0 mt-2 w-44 rounded-md bg-white border border-gray-200 z-20" style="display: none;">'
            '    <div class="py-1">'
            '      <a hx-get="{}" hx-target="#main-content" hx-push-url="true" class="cursor-pointer block px-4 py-2 text-[14px] text-gray-700 hover:bg-gray-50 flex items-center gap-2"><i data-lucide="edit-3" class="w-4 h-4"></i> Edit</a>'
            '      <a href="{}" target="_blank" class="block px-4 py-2 text-[14px] text-gray-700 hover:bg-gray-50 flex items-center gap-2"><i data-lucide="external-link" class="w-4 h-4"></i> View on Site</a>'
            '      {}{}'
            '      {}'
            '    </div>'
            '  </div>'
            '</div>',
            edit_url, view_url, approve_btn, reject_btn, delete_btn
        )
