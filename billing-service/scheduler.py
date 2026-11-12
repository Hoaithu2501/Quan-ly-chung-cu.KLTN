"""Run one scheduler per Billing process (one replica in the demo compose file)."""

import atexit
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler(app):
    if os.getenv("DISABLE_SCHEDULER", "false").lower() in ("1", "true", "yes") or os.getenv(
        "SCHEDULER_ENABLED", "true"
    ).lower() in ("0", "false", "no"):
        return None
    if app.extensions.get("billing_scheduler"):
        return app.extensions["billing_scheduler"]
    jobs = app.extensions["billing_jobs"]

    def overdue_job():
        with app.app_context():
            try:
                jobs["overdue"]()
                jobs["reminders"]()
            except Exception:
                logging.getLogger(__name__).exception("Daily overdue scan failed")

    def outbox_job():
        with app.app_context():
            try:
                jobs["outbox"]()
            except Exception:
                logging.getLogger(__name__).exception("Outbox delivery failed; will retry")

    def sepay_job():
        with app.app_context():
            try:
                jobs["sepay"]()
            except Exception:
                logging.getLogger(__name__).exception("SePay reconciliation failed; verified ledger retained")

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    # A laptop may sleep overnight. Run a missed daily scan on resume instead
    # of leaving invoices unpaid until the following day; coalesce catches up once.
    scheduler.add_job(
        overdue_job,
        "cron",
        hour=0,
        minute=5,
        id="overdue-daily",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=None,
    )
    scheduler.add_job(outbox_job, "interval", seconds=30, id="billing-outbox", max_instances=1, coalesce=True)
    scheduler.add_job(sepay_job, "interval", seconds=60, id="billing-sepay", max_instances=1, coalesce=True)
    scheduler.start()
    app.extensions["billing_scheduler"] = scheduler
    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler.running else None)
    # Reconcile downtime before serving requests, without depending on peer uptime.
    overdue_job()
    return scheduler
