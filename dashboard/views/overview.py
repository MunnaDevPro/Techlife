import json
from django.shortcuts import render
from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from dashboard.services import overview_service

@staff_required
def overview(request):
    kpis = overview_service.get_kpi_counts()
    chart_data = overview_service.get_posts_chart_data()
    recent_activity = overview_service.get_recent_activity()
    
    ctx = get_dashboard_context(request, "Overview", "Overview")
    ctx.update({
        "kpis": kpis,
        "chart_labels": json.dumps(chart_data["labels"]),
        "chart_values": json.dumps(chart_data["values"]),
        "recent_activity": recent_activity,
    })
    return render(request, "dashboard/overview.html", ctx)
