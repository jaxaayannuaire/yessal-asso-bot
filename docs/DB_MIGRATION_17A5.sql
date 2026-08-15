-- Additive migration used by Phase 17A.5
CREATE TABLE IF NOT EXISTS telegram_link_tokens (
    token_hash VARCHAR PRIMARY KEY,
    dolibarr_user_id VARCHAR NOT NULL,
    created_by_telegram_id VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
