"""
PostgreSQL client for multi-tenant configs and audit logs.
Connection pooling with retry logic. Uses DATABASE_URL from environment.
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{os.getenv('POSTGRES_USER', 'osint')}:{os.getenv('POSTGRES_PASSWORD', 'dev_postgres_secret')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'osint_platform')}"
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    service_name VARCHAR(64) NOT NULL,
    encrypted_api_key TEXT,
    UNIQUE(tenant_id, service_name)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    action VARCHAR(128) NOT NULL,
    target VARCHAR(512),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(32) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_tenant ON audit_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
"""


def _get_connection(max_retries: int = 5, retry_delay: float = 2.0):
    """Get a connection with retry logic."""
    try:
        import psycopg2
        from psycopg2 import pool
    except ImportError:
        raise ImportError("psycopg2-binary required for PostgreSQL support")

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            logger.warning("PostgreSQL connection attempt %d failed: %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            raise


@contextmanager
def get_connection() -> Iterator[Any]:
    """Context manager for a single connection. Handles disconnect gracefully."""
    conn = None
    try:
        conn = _get_connection()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("PostgreSQL error: %s", e)
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def ensure_schema() -> None:
    """Create tables if they do not exist."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA_SQL)
    except Exception as e:
        logger.warning("Schema setup failed (PostgreSQL may be unavailable): %s", e)


def fetch_service_credentials(tenant_id: Optional[str], service: str) -> Dict[str, str]:
    """
    Fetch credentials from user_configs for the given tenant and service.
    Returns empty dict if not found or tenant_id is None.
    """
    if not tenant_id:
        return {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT encrypted_api_key FROM user_configs
                    WHERE tenant_id = %s::uuid AND service_name = %s
                    """,
                    (tenant_id, service.lower()),
                )
                row = cur.fetchone()
                if row and row[0]:
                    raw = row[0]
                    if isinstance(raw, str):
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            return {"api_key": raw} if service == "shodan" else {}
                    else:
                        data = raw
                    return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("fetch_service_credentials failed: %s", e)
    return {}


def log_audit_event(
    tenant_id: Optional[str],
    action: str,
    target: Optional[str] = None,
    status: str = "initiated",
) -> None:
    """Insert an audit event record."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_events (tenant_id, action, target, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (tenant_id if tenant_id else None, action, target or "", status),
                )
    except Exception as e:
        logger.warning("log_audit_event failed: %s", e)
