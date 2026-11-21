"""Lease reminders: residents 30 days before a lease ends, management on the end date."""

import atexit
from datetime import datetime, timedelta
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler(app):
    if os.getenv("DISABLE_SCHEDULER", "false").lower() in ("1", "true", "yes") or os.getenv(
        "SCHEDULER_ENABLED", "true"
    ).lower() in ("0", "false", "no"):
        return None
    if app.extensions.get("resident_scheduler"):
        return app.extensions["resident_scheduler"]

    def leases():
        with app.app_context():
            try:
                app.extensions["resident_jobs"]["leases"]()
            except Exception:
                logging.getLogger(__name__).exception("Lease reminders failed; will retry next hour")

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    # Hourly, because every notice has a fixed event id and is sent only once. The first run
    # waits a minute so the notification service is up after a restart.
    scheduler.add_job(
        leases,
        "interval",
        hours=1,
        id="lease-reminders",
        max_instances=1,
        coalesce=True,
        # A run missed while the computer slept still happens once on wake.
        misfire_grace_time=None,
        next_run_time=datetime.now() + timedelta(minutes=1),
    )
    scheduler.start()
    app.extensions["resident_scheduler"] = scheduler
    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler.running else None)
    return scheduler
