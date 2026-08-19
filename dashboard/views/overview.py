import json
from django.shortcuts import render
from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from dashboard.services import overview_service

@staff_required
def overview(request):
    kpis = overview_service.get_kpi_counts()
    chart_data = overview_service.get_posts_chart_data()
    forum_chart_data = overview_service.get_forum_chart_data()
    category_data = overview_service.get_posts_by_category()
    user_data = overview_service.get_user_stats()
    recent_activity = overview_service.get_recent_activity()
    automation_ops = overview_service.get_automation_operations_stats()
    
    ctx = get_dashboard_context(request, "Overview", "Overview")
    ctx.update({
        "kpis": kpis,
        "chart_labels": json.dumps(chart_data["labels"]),
        "chart_values": json.dumps(chart_data["values"]),
        "forum_chart_labels": json.dumps(forum_chart_data["labels"]),
        "forum_question_values": json.dumps(forum_chart_data["question_values"]),
        "forum_answer_values": json.dumps(forum_chart_data["answer_values"]),
        "category_labels": json.dumps(category_data["labels"]),
        "category_values": json.dumps(category_data["values"]),
        "category_list": zip(category_data["labels"], category_data["values"]),
        "user_labels": json.dumps(user_data["labels"]),
        "user_values": json.dumps(user_data["values"]),
        "recent_activity": recent_activity,
        "automation_ops": automation_ops,
    })
    return render(request, "dashboard/overview.html", ctx)
