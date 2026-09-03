import sys

code = '''
class CompanyTable(tables.Table):
    selection = tables.CheckBoxColumn(
        accessor='pk',
        attrs={
            "th": {"class": "!py-4 !pl-4 !pr-3.5 !w-6 !text-left"},
            "th__input": {"class": "!cursor-pointer !rounded !border-gray-300 !text-blue-600 focus:!ring-blue-500", "@change": "selectAll($el.checked)"},
            "td": {"class": "!py-4 !pl-4 !pr-3.5 !w-6 !align-middle"},
            "td__input": {"class": "post-select !cursor-pointer !rounded !border-gray-300 !text-blue-600 focus:!ring-blue-500"}
        },
        orderable=False
    )
    
    serial_number = tables.Column(
        empty_values=(),
        verbose_name='S/N',
        attrs={
            "th": {"class": "!py-4 !pl-3.5 !pr-4 !w-8 !text-center !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!py-4 !pl-3.5 !pr-4 !w-8 !text-center !align-middle !whitespace-nowrap"}
        },
        orderable=False
    )
    
    thumbnail = tables.Column(
        empty_values=(), 
        orderable=False,
        verbose_name='Logo',
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !w-16 !whitespace-nowrap"}
        }
    )
    
    title = tables.Column(
        verbose_name="Company Name",
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !text-[12px] !font-bold !text-gray-900 !w-[220px] !max-w-[220px] !break-words"}
        }
    )
    
    company_email = tables.Column(
        verbose_name="Email",
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !text-[13px] !text-gray-600 !whitespace-nowrap"}
        }
    )

    company_phone = tables.Column(
        verbose_name="Phone",
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !text-[13px] !text-gray-600 !whitespace-nowrap"}
        }
    )
    
    category = tables.Column(
        accessor='category.name',
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !text-[13px] !text-gray-600 !font-medium !whitespace-nowrap"}
        }
    )
    
    status = tables.Column(
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !whitespace-nowrap"}
        }
    )
    
    created_at = tables.DateTimeColumn(
        format='Y-m-d', 
        verbose_name="Registered Date",
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !text-[13px] !text-gray-400 !whitespace-nowrap"}
        }
    )
    
    actions = tables.Column(
        empty_values=(), 
        orderable=False, 
        verbose_name="Actions",
        attrs={
            "th": {"class": "!p-4 !text-left !text-[11px] !font-bold !text-gray-500 !uppercase !tracking-wider !whitespace-nowrap"},
            "td": {"class": "!p-4 !align-middle !whitespace-nowrap"}
        }
    )

    class Meta:
        model = BlogPost
        fields = ("selection", "serial_number", "thumbnail", "title", "company_email", "company_phone", "category", "status", "created_at", "actions")
        attrs = {
            "class": "!min-w-full !w-full !table-auto !divide-y !divide-gray-200 !border-collapse",
            "thead": {"class": "!bg-gray-50/75"},
            "tbody": {"class": "!divide-y !divide-gray-100 !bg-white"},
        }

    def render_title(self, record, value):
        detail_url = f"/dashboard/content/posts/{record.pk}/"
        return format_html('<a href="{}" class="hover:!text-blue-600 transition-colors" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; max-height: 2.8em; line-height: 1.4;">{}</a>', detail_url, value)

    def render_thumbnail(self, record):
        detail_url = f"/dashboard/content/posts/{record.pk}/"
        if record.featured_image:
            img_html = format_html('<img src="{}" class="w-10 h-10 object-cover rounded-md border border-gray-200">', record.featured_image.url)
        elif record.featured_image_url:
            img_html = format_html('<img src="{}" class="w-10 h-10 object-cover rounded-md border border-gray-200">', record.featured_image_url)
        else:
            img_html = format_html('<div class="w-10 h-10 bg-gray-100 rounded-md border border-gray-200 flex items-center justify-center text-gray-400"><i data-lucide="image" class="w-5 h-5"></i></div>')
        return format_html('<a href="{}" class="inline-block transition-transform hover:scale-105">{}</a>', detail_url, img_html)

    def render_company_email(self, value):
        return value if value else "-"

    def render_company_phone(self, value):
        return value if value else "-"

    def render_status(self, record, value):
        val = str(value).lower()
        if val == "published":
            bg_cls = "!bg-green-50 !text-green-700 !border-green-200 hover:!bg-green-100"
            icon = "check-circle"
        elif val in ["pending", "edited"]:
            bg_cls = "!bg-yellow-50 !text-yellow-700 !border-yellow-200 hover:!bg-yellow-100"
            icon = "clock"
        elif val == "rejected":
            bg_cls = "!bg-red-50 !text-red-700 !border-red-200 hover:!bg-red-100"
            icon = "x-circle"
        else:
            bg_cls = "!bg-blue-50 !text-blue-700 !border-blue-200 hover:!bg-blue-100"
            icon = "info"
            
        return format_html(
            \'\'\'<button type="button" @click="$dispatch(\'open-status-modal\', {{ id: \'{}\', status: \'{}\' }})" \'\'\'
            \'\'\'class="!inline-flex !items-center !px-2.5 !py-0.5 !rounded-full !text-[11px] !font-bold !border !transition-colors !cursor-pointer {}" \'\'\'
            \'\'\'title="Click to change status">\'\'\'
            \'\'\'<i data-lucide="{}" class="!w-3.5 !h-3.5 !mr-1.5"></i>{}\'\'\'
            \'\'\'</button>\'\'\',
            record.pk,
            val,
            bg_cls,
            icon,
            str(value).title()
        )

    def render_actions(self, record):
        edit_url = f"/dashboard/content/posts/{record.pk}/edit/"
        view_url = f"/details/{record.slug}/"
        
        edit_btn = format_html(
            \'\'\'<a href="{}" \'\'\'
            \'\'\'   class="!inline-flex !items-center !justify-center !w-8 !h-8 !rounded-lg !border !border-gray-200 !bg-white !text-gray-600 hover:!bg-gray-50 hover:!text-gray-900 hover:!border-gray-300 !transition-all !cursor-pointer" \'\'\'
            \'\'\'   title="Edit Company">\'\'\'
            \'\'\'  <i data-lucide="edit-3" class="w-4 h-4"></i>\'\'\'
            \'\'\'</a>\'\'\',
            edit_url
        )
        
        view_btn = format_html(
            \'\'\'<a href="{}" target="_blank" \'\'\'
            \'\'\'   class="!inline-flex !items-center !justify-center !w-8 !h-8 !rounded-lg !border !border-gray-200 !bg-white !text-gray-600 hover:!bg-gray-50 hover:!text-gray-900 hover:!border-gray-300 !transition-all !cursor-pointer" \'\'\'
            \'\'\'   title="View on Site">\'\'\'
            \'\'\'  <i data-lucide="external-link" class="w-4 h-4"></i>\'\'\'
            \'\'\'</a>\'\'\',
            view_url
        )

        delete_btn = format_html(
            \'\'\'<button type="button" @click="confirmDeleteId = {}; showDeleteModal = true" \'\'\'
            \'\'\'        class="!inline-flex !items-center !justify-center !w-8 !h-8 !rounded-lg !border !border-red-100 !bg-red-50 !text-red-600 hover:!bg-red-100 hover:!text-red-700 hover:!border-red-200 !transition-all !cursor-pointer" \'\'\'
            \'\'\'        title="Delete Company">\'\'\'
            \'\'\'  <i data-lucide="trash-2" class="w-4 h-4"></i>\'\'\'
            \'\'\'</button>\'\'\',
            record.pk
        )

        return format_html(
            '<div class="!flex !items-center !gap-1.5">'
            '  {}'
            '  {}'
            '  {}'
            '</div>',
            edit_btn, view_btn, delete_btn
        )
'''

with open(r'd:\Techlife\Techlife\dashboard\tables.py', 'a', encoding='utf-8') as f:
    f.write(code)
