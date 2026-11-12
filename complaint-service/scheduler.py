"""Retry saved management-reply notifications after transient delivery failures."""

import atexit
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler(app):
    if os.getenv("DISABLE_SCHEDULER", "false").lower() in ("1", "true", "yes") or os.getenv(
        "SCHEDULER_ENABLED", "true"
    ).lower() in ("0", "false", "no"):
        return None
    if app.extensions.get("complaint_scheduler"):
        return app.extensions["complaint_scheduler"]

    def deliver():
        with app.app_context():
            try:
                app.extensions["complaint_jobs"]["outbox"]()
            except Exception:
                logging.getLogger(__name__).exception("Complaint notification delivery failed; will retry")

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(deliver, "interval", seconds=30, id="complaint-notifications", max_instances=1, coalesce=True)
    scheduler.start()
    app.extensions["complaint_scheduler"] = scheduler
    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler.running else None)
    return scheduler
