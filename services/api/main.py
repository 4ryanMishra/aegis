"""
AEGIS Verification Engine API Service.
FastAPI REST server implementing endpoints for the AEGIS first vertical slice.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.models.schema import ScenarioRecord, ScenarioRunRequest
from src.core.coordinator import VerificationCoordinator
from src.validators.registry import default_registry
from src.config import default_config

app = FastAPI(
    title="AEGIS — Oracle Verification Engine API",
    description="Adaptive Oracle Verification & Risk Engine for delayed oracle architectures.",
    version="0.1.0-mvp",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

coordinator = VerificationCoordinator()


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "AEGIS Verification Engine",
        "version": "0.1.0-mvp",
        "environment": default_config.environment,
        "active_strategies": len(default_registry.list_strategies()),
    }


@app.get("/api/scenarios")
def list_scenarios():
    """List all available deterministic test scenarios."""
    return coordinator.list_scenarios()


@app.post("/api/scenarios/run", response_model=ScenarioRecord)
def run_scenario(req: ScenarioRunRequest):
    """Execute or step through a 1-hour verification window simulation."""
    try:
        return coordinator.run_scenario(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategies")
def list_strategies():
    """List pluggable validator strategies and their active versions."""
    return default_registry.list_strategies()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
