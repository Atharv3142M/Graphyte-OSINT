#!/usr/bin/env python3
"""
Infrastructure sanity checker for Unified OSINT Platform.
Verifies connectivity to all 5 data stores. Run from backend/: python scripts/check_services.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TIMEOUT = 5
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or "redis://localhost:6379/0"
PG_URL = os.getenv("DATABASE_URL") or f"postgresql://{os.getenv('POSTGRES_USER','osint')}:{os.getenv('POSTGRES_PASSWORD','dev_postgres_secret')}@{os.getenv('POSTGRES_HOST','localhost')}:{os.getenv('POSTGRES_PORT','5432')}/{os.getenv('POSTGRES_DB','osint_platform')}"
RABBITMQ_URL = os.getenv("RABBITMQ_URL") or f"amqp://{os.getenv('RABBITMQ_USER','admin')}:{os.getenv('RABBITMQ_PASSWORD','dev_rabbitmq_secret')}@{os.getenv('RABBITMQ_HOST','localhost')}:{os.getenv('RABBITMQ_AMQP_PORT','5672')}/"
NEO4J_URI = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
WEAVIATE_URL = os.getenv("WEAVIATE_HTTP_URI") or "http://localhost:8080"


def check_postgres() -> tuple[bool, str]:
    try:
        import psycopg2
        conn = psycopg2.connect(PG_URL, connect_timeout=TIMEOUT)
        cur = conn.cursor()
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants')")
        cur.close()
        conn.close()
        return True, "Connected & schema verified."
    except ImportError:
        return False, "psycopg2-binary not installed."
    except Exception as e:
        return False, str(e)


def check_redis() -> tuple[bool, str]:
    try:
        from redis import Redis
        r = Redis.from_url(REDIS_URL, socket_connect_timeout=TIMEOUT)
        r.ping()
        r.close()
        return True, "PING successful."
    except ImportError:
        return False, "redis package not installed."
    except Exception as e:
        return False, str(e)


def check_rabbitmq() -> tuple[bool, str]:
    try:
        import pika
        params = pika.URLParameters(RABBITMQ_URL)
        params.socket_timeout = TIMEOUT
        conn = pika.BlockingConnection(params)
        conn.close()
        return True, "Connection established."
    except ImportError:
        return False, "pika package not installed."
    except Exception as e:
        return False, str(e)


def check_neo4j() -> tuple[bool, str]:
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "dev_neo4j_secret")),
            connection_timeout=TIMEOUT,
        )
        driver.verify_connectivity()
        driver.close()
        return True, "Bolt connection successful."
    except ImportError:
        return False, "neo4j package not installed."
    except Exception as e:
        return False, str(e)


def check_weaviate() -> tuple[bool, str]:
    try:
        import urllib.request
        req = urllib.request.Request(WEAVIATE_URL + "/v1/.well-known/ready", method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                return True, "REST endpoint HTTP 200 OK."
            return False, f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


def main():
    checks = [
        ("PostgreSQL (Port 5432)", check_postgres),
        ("Redis (Port 6379)", check_redis),
        ("RabbitMQ (Port 5672)", check_rabbitmq),
        ("Neo4j (Port 7687)", check_neo4j),
        ("Weaviate (Port 8080)", check_weaviate),
    ]
    print("Unified OSINT Platform - Infrastructure Sanity Check")
    print("=" * 60)
    all_ok = True
    for name, fn in checks:
        ok, msg = fn()
        status = "[x]" if ok else "[ ]"
        print(f"  {status} {name} - {msg}")
        if not ok:
            all_ok = False
    print("=" * 60)
    if all_ok:
        print("All services healthy. Ready for E2E testing.")
    else:
        print("Some services failed. Ensure Docker containers are running:")
        print("  docker compose up -d")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
