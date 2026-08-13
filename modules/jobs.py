import logging
from telegram.ext import ContextTypes
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager

logger = logging.getLogger(__name__)

async def background_sync_job(context: ContextTypes.DEFAULT_TYPE):
    """Job automatique : Synchronise en arrière-plan les contacts et membres depuis Dolibarr"""
    logger.info("⏳ Lancement du job de synchronisation automatique en arrière-plan...")
    
    client = DolibarrClient()
    db = DatabaseManager()
    
    try:
        # 1. Sync Contacts
        success_c, data_c = client.get_contacts()
        if success_c:
            db.sync_contacts(data_c)
            logger.info("✅ Job auto : Contacts synchronisés.")
            
        # 2. Sync Membres (Adhérents)
        success_m, data_m = client.get_members()
        if success_m:
            db.sync_members(data_m)
            logger.info("✅ Job auto : Adhérents synchronisés.")
            
    except Exception as e:
        logger.error(f"❌ Erreur dans background_sync_job : {e}")
    finally:
        db.close()