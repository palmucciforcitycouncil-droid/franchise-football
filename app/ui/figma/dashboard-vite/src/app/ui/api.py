"""
Main FastAPI application for Franchise Football.
Includes stats API router and other endpoints.
"""

from fastapi import FastAPI
from app.ui.api_stats import router as stats_router

app = FastAPI(
    title="Franchise Football API",
    description="Advanced Stats API for Franchise Football",
    version="1.0.0"
)

# Include stats router
app.include_router(stats_router)

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Franchise Football Advanced Stats API",
        "version": "1.0.0",
        "endpoints": {
            "stats": "/api/stats",
            "health": "/api/stats/health"
        }
    }

@app.get("/health")
def health_check():
    """Global health check."""
    return {"status": "healthy", "service": "franchise_football_api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8015)
