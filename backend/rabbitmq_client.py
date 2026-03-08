"""
RabbitMQ enterprise event bus client.
Publishes lifecycle events to osint_events topic exchange.
Uses RABBITMQ_URL from environment. Handles disconnects with retry logic.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

def _rabbitmq_url() -> str:
    url = os.getenv("RABBITMQ_URL")
    if url:
        return url
    user = os.getenv("RABBITMQ_USER", "admin")
    password = os.getenv("RABBITMQ_PASSWORD", "dev_rabbitmq_secret")
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = os.getenv("RABBITMQ_AMQP_PORT", "5672")
    vhost = os.getenv("RABBITMQ_VHOST", "/")
    if vhost == "/":
        return f"amqp://{user}:{password}@{host}:{port}/"
    return f"amqp://{user}:{password}@{host}:{port}/{vhost}"


RABBITMQ_URL = _rabbitmq_url()
EXCHANGE_NAME = "osint_events"
MAX_RETRIES = 5
RETRY_DELAY = 2.0


async def publish_enterprise_event(routing_key: str, payload: Dict[str, Any]) -> bool:
    """
    Publish an event to the osint_events topic exchange.
    Returns True on success, False on failure (logs and returns).
    """
    try:
        import aio_pika
        from aio_pika import Message, DeliveryMode
    except ImportError:
        logger.warning("aio_pika not installed; skipping RabbitMQ publish")
        return False

    for attempt in range(MAX_RETRIES):
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
                body = json.dumps(payload).encode("utf-8")
                await exchange.publish(
                    Message(body=body, delivery_mode=DeliveryMode.PERSISTENT),
                    routing_key=routing_key,
                )
                return True
        except Exception as e:
            logger.warning("RabbitMQ publish attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
            return False
    return False


def publish_enterprise_event_sync(routing_key: str, payload: Dict[str, Any]) -> bool:
    """Synchronous publish (for use from sync endpoints and agent nodes)."""
    try:
        import pika
    except ImportError:
        logger.warning("pika not installed; skipping RabbitMQ publish")
        return False

    params = pika.URLParameters(RABBITMQ_URL)
    for attempt in range(MAX_RETRIES):
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
            body = json.dumps(payload).encode("utf-8")
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            connection.close()
            return True
        except Exception as e:
            logger.warning("RabbitMQ sync publish attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES - 1:
                import time
                time.sleep(RETRY_DELAY)
            return False
    return False
