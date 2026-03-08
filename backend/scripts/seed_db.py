#!/usr/bin/env python3
"""
Database seeder for Unified OSINT Platform.
Seeds default tenant (Alpha Corp) and mock user_configs for Shodan/Censys.
Run from backend/: python scripts/seed_db.py
"""
from __future__ import annotations

import json
import os
import sys

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default tenant UUID (deterministic for X-Tenant-ID header)
DEFAULT_TENANT_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TENANT_NAME = "Alpha Corp"
TENANT_CODE = "default-alpha-001"

MOCK_SHODAN = {"api_key": "mock_shodan_api_key_placeholder"}
MOCK_CENSYS = {"api_id": "mock_censys_id_placeholder", "api_secret": "mock_censys_secret_placeholder"}


def seed() -> bool:
    """Seed default tenant and mock configs. Returns True on success."""
    try:
        from postgres_client import get_connection, ensure_schema, DATABASE_URL
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}. Run from backend/ with: python scripts/seed_db.py")
        return False

    print("Seeding PostgreSQL database...")
    print(f"  DATABASE_URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else '(from env)'}")

    try:
        ensure_schema()
    except Exception as e:
        print(f"[ERROR] Schema setup failed: {e}")
        return False

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Upsert default tenant (PostgreSQL 9.5+ ON CONFLICT)
                cur.execute(
                    """
                    INSERT INTO tenants (id, name)
                    VALUES (%s::uuid, %s)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                    """,
                    (DEFAULT_TENANT_UUID, TENANT_NAME),
                )

                # Upsert user_configs (shodan, censys)
                for service, payload in [("shodan", MOCK_SHODAN), ("censys", MOCK_CENSYS)]:
                    cur.execute(
                        """
                        INSERT INTO user_configs (tenant_id, service_name, encrypted_api_key)
                        VALUES (%s::uuid, %s, %s)
                        ON CONFLICT (tenant_id, service_name)
                        DO UPDATE SET encrypted_api_key = EXCLUDED.encrypted_api_key
                        """,
                        (DEFAULT_TENANT_UUID, service, json.dumps(payload)),
                    )

        print("[OK] Default tenant and mock configs seeded.")
        print(f"  Tenant: {TENANT_NAME} (code: {TENANT_CODE})")
        print(f"  UUID:   {DEFAULT_TENANT_UUID}")
        print(f"  Use header: X-Tenant-ID: {DEFAULT_TENANT_UUID}")
        return True
    except Exception as e:
        print(f"[ERROR] Seed failed: {e}")
        return False


if __name__ == "__main__":
    ok = seed()
    sys.exit(0 if ok else 1)
