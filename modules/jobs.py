"""Jobs planifiés de Yessal Asso Bot."""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from telegram.ext import ContextTypes

from core.db import DatabaseManager
from services.sync_service import SyncService

logger = logging.getLogger(__name__)


def _run_profile(profile: str):
    service = SyncService()
    try:
        return service.sync_profile(profile)
    finally:
        service.close()


async def sync_contacts_members_job(context: ContextTypes.DEFAULT_TYPE):
    """Synchronisation des contacts et adhérents toutes les 30 minutes."""
    results = _run_profile("contacts_members")
    logger.info("Sync contacts/adhérents : %s", results)


async def sync_finance_job(context: ContextTypes.DEFAULT_TYPE):
    """Synchronisation adhésions et cotisations toutes les 15 minutes."""
    results = _run_profile("finance")
    logger.info("Sync finance : %s", results)


async def background_sync_job(context: ContextTypes.DEFAULT_TYPE):
    """Synchronisation complète de sécurité, par défaut toutes les heures."""
    results = _run_profile("full")
    logger.info("Synchronisation complète : %s", results)


async def backup_duckdb_job(context: ContextTypes.DEFAULT_TYPE):
    """Crée une copie complète quotidienne de DuckDB."""
    source = Path(os.getenv("DUCKDB_PATH", "./data/yessal_asso.duckdb"))
    backup_dir = Path(os.getenv("DUCKDB_BACKUP_DIR", "./data/backups"))
    if not source.exists():
        logger.warning("Sauvegarde ignorée : DuckDB introuvable : %s", source)
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"yessal_asso_{datetime.now():%Y-%m-%d}.duckdb"
    shutil.copy2(source, target)
    logger.info("Sauvegarde DuckDB créée : %s", target)


async def scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    chat_id = os.getenv("ADMIN_CHAT_ID")
    if not chat_id:
        logger.warning("ADMIN_CHAT_ID non défini")
        return
    db = DatabaseManager()
    try:
        success, data = db.get_weekly_report_data()
    finally:
        db.close()
    if not success:
        return
    text = (
        "📊 *RAPPORT HEBDOMADAIRE AUTOMATIQUE - YESSAL ASSO*\n\n"
        f"👥 Total adhérents : {data.get('total_members', 0)}\n"
        f"🟢 Adhérents actifs : {data.get('active_members', 0)}\n"
        f"💰 Cotisations : {data.get('total_cotisations_amount', 0):,.0f} FCFA"
    )
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
