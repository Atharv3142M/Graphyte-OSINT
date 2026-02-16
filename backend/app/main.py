from fastapi import FastAPI


app = FastAPI(
    title="OSINT Visualizer API",
    version="0.1.0",
    description="Backend API for the OSINT Digital Footprint Visualizer.",
)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Basic health check endpoint to verify that the API is running.
    """
    return {"status": "ok"}


