#!/usr/bin/env python3
"""Entry point: Production Graphyte OSINT Platform."""
import os
import sys
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging before any other imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    from backend.settings import settings
    
    logger.info("=" * 80)
    logger.info("GRAPHYTE OSINT PLATFORM - Starting Backend")
    logger.info("=" * 80)
    logger.info(f"API Title: {settings.API_TITLE}")
    logger.info(f"API Version: {settings.API_VERSION}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"Auth Required: {settings.AUTH_REQUIRED}")
    logger.info(f"Redis URL: {settings.REDIS_URL}")
    logger.info(f"Database URL: {settings.DATABASE_URL[:50]}...")
    logger.info(f"Neo4j URI: {settings.NEO4J_URI}")
    logger.info("=" * 80)
    
    # Run application
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
        t_celery = None
        if "CELERY" in procs:
            t_celery = threading.Thread(
                target=_stream_output,
                args=("CELERY", CELERY_COLOR, procs["CELERY"]),
                daemon=True,
            )
        t_next = threading.Thread(
            target=_stream_output,
            args=("NEXTJS", NEXT_COLOR, procs["NEXTJS"]),
            daemon=True,
        )
        threads.extend([t_fastapi, t_next])
        if t_celery:
            threads.append(t_celery)
        for t in threads:
            t.start()

        stop = threading.Event()

        def handle_sigint(signum, frame):  # type: ignore[override]
            print("\n[CTRL+C] Stopping all services...")
            stop.set()

        signal.signal(signal.SIGINT, handle_sigint)

        # Wait until interrupted
        while not stop.is_set():
            time.sleep(0.5)
            # If any core process exits unexpectedly, stop everything
            if any(p.poll() not in (None, 0) for p in procs.values()):
                print("[WARN] One or more processes exited unexpectedly. Shutting down...")
                stop.set()

    finally:
        for name, proc in procs.items():
            _terminate(name, proc)
        for t in threads:
            t.join(timeout=2)

    print("All services stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

