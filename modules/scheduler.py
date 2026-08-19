"""Configuration centralisée des tâches planifiées du bot."""
from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from modules.jobs import (
    backup_duckdb_job,
    background_sync_job,
    scheduled_weekly_report,
    sync_contacts_members_job,
    sync_finance_job,
)

logger = logging.getLogger(__name__)

DAKAR_TZ = ZoneInfo("Africa/Dakar")


def configure_scheduled_jobs(app) -> bool:
    """Enregistre les tâches périodiques disponibles dans la JobQueue.

    Les fréquences suivent le niveau de volatilité actuellement pris en
    charge par le moteur de synchronisation. Les futurs composants
    (caisse, produits, services, utilisateurs, etc.) seront ajoutés ici
    dès que leur synchronisation DuckDB existera.
    """
    job_queue = getattr(app, "job_queue", None)
    if not job_queue:
        logger.warning("JobQueue indisponible : jobs automatiques désactivés.")
        return False

    job_queue.run_repeating(
        sync_finance_job,
        interval=15 * 60,
        first=15,
        name="sync_finance_15m",
    )
    job_queue.run_repeating(
        sync_contacts_members_job,
        interval=30 * 60,
        first=30,
        name="sync_contacts_members_30m",
    )
    job_queue.run_repeating(
        background_sync_job,
        interval=60 * 60,
        first=60,
        name="sync_full_hourly",
    )
    job_queue.run_daily(
        backup_duckdb_job,
        time=time(hour=6, minute=0, tzinfo=DAKAR_TZ),
        name="backup_duckdb_daily",
    )
    job_queue.run_repeating(
        scheduled_weekly_report,
        interval=7 * 24 * 60 * 60,
        first=7 * 24 * 60 * 60,
        name="weekly_report",
    )

    logger.info(
        "JobQueue configurée : finance 15 min, contacts/adhérents 30 min, "
        "sync complète 1 h, sauvegarde DuckDB 06h00 Dakar, rapport hebdomadaire."
    )
    return True
