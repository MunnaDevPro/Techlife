# dashboard/tasks.py
"""
Celery configuration and tasks for the TechLife dashboard.

Infrastructure Requirements:
1. Redis Server: Celery relies on a broker to send/receive messages.
   - Install Redis on the Contabo VPS (e.g., `sudo apt-get install redis-server`).
   - Confirm it is running: `redis-cli ping` (should reply PONG).
2. Broker URL: Add CELERY_BROKER_URL = 'redis://localhost:6379/0' to Django base.py settings.
3. Start Celery Worker: `celery -A root worker -l info`
4. Start Celery Beat Scheduler: `celery -A root beat -l info`
"""

from celery import shared_task
from dashboard.services.analytics_service import compute_daily_rollup

@shared_task
def run_compute_daily_rollup():
    """
    Celery periodic task running nightly to aggregate real post view, comment,
    and like statistics and populate the rollup table.
    """
    stats_count = compute_daily_rollup()
    return f"Rollup finished. Upserted {stats_count} daily stat records."
