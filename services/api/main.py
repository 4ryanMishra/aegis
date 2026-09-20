"""
AEGIS Verification Engine API Service.
FastAPI REST server implementing endpoints for the AEGIS first vertical slice.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
try:
    from services.api.src.models.schema import (
        ScenarioRecord,
        ScenarioRunRequest,
        SimulationResetRequest,
        SimulationStepRequest,
        SimulationConfigRequest,
        PositionUpdateRequest,
    )
    from services.api.src.core.coordinator import VerificationCoordinator
    from services.api.src.core.simulation_engine import SimulationEngine
    from services.api.src.validators.registry import default_registry
    from services.api.src.config import default_config
except ImportError:
    from src.models.schema import (
        ScenarioRecord,
        ScenarioRunRequest,
        SimulationResetRequest,
        SimulationStepRequest,
        SimulationConfigRequest,
        PositionUpdateRequest,
    )
    from src.core.coordinator import VerificationCoordinator
    from src.core.simulation_engine import SimulationEngine
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
simulation_engine = SimulationEngine()


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


# -------------------------------------------------------------
# Real-Time Continuous Simulation Engine Endpoints
# -------------------------------------------------------------

@app.get("/api/simulation/state")
def get_simulation_state():
    """Retrieve instantaneous authoritative snapshot of continuous simulation."""
    try:
        return simulation_engine.get_snapshot()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/start")
def start_simulation():
    """Start or resume continuous simulation."""
    simulation_engine.start()
    return {"status": "RUNNING", "state": simulation_engine.get_snapshot()}


@app.post("/api/simulation/pause")
def pause_simulation():
    """Pause continuous simulation."""
    simulation_engine.pause()
    return {"status": "PAUSED", "state": simulation_engine.get_snapshot()}


@app.post("/api/simulation/reset")
def reset_simulation(req: SimulationResetRequest):
    """Reset simulation clock to T0 for the selected scenario."""
    simulation_engine.reset(scenario_id=req.scenario_id, ltv=req.ltv_factor, seed=req.seed or 42)
    return {"status": "RESET", "state": simulation_engine.get_snapshot()}


@app.post("/api/simulation/step")
def step_simulation(req: SimulationStepRequest):
    """Advance simulation clock by delta_seconds (e.g. +15m demo step)."""
    simulation_engine.step(delta_seconds=req.delta_seconds if req.delta_seconds is not None else 900.0)
    return {"status": "STEPPED", "state": simulation_engine.get_snapshot()}


@app.post("/api/simulation/finalize")
def finalize_simulation():
    """Immediately finalize verification window at 3600s."""
    simulation_engine.finalize()
    return {"status": "FINALIZED", "state": simulation_engine.get_snapshot()}


@app.post("/api/simulation/config")
def config_simulation(req: SimulationConfigRequest):
    """Update speed multiplier or scenario parameters."""
    if req.speed_multiplier is not None:
        simulation_engine.set_speed(req.speed_multiplier)
    if req.scenario_id is not None:
        simulation_engine.reset(scenario_id=req.scenario_id, ltv=req.ltv_factor)
    return {"status": "UPDATED", "state": simulation_engine.get_snapshot()}


@app.post("/api/simulation/position")
def update_position(req: PositionUpdateRequest):
    """Update downstream collateral position or borrow amount."""
    simulation_engine.update_position(
        collateral_amount=req.collateral_amount,
        debt_amount=req.debt_amount,
        set_max_borrow=req.set_max_borrow or False,
    )
    return {"status": "UPDATED", "state": simulation_engine.get_snapshot()}


@app.get("/api/strategies")
def list_strategies():
    """List pluggable validator strategies and their active versions."""
    return default_registry.list_strategies()


@app.get("/api/benchmarks/summary")
def get_benchmark_summary():
    """Execute rolling 1-hour out-of-sample benchmark evaluation across baseline reference methodologies."""
    from packages.quant.src.dataset import generate_synthetic_rwa_series
    from packages.quant.src.baseline_strategies import (
        NaivePersistenceStrategy,
        SimpleMovingAverageStrategy,
        ExponentialMovingAverageStrategy,
    )
    from packages.quant.src.benchmark import ValidatorBenchmarkRunner

    dataset = generate_synthetic_rwa_series(
        dataset_name="synthetic_rwa_gold_benchmark",
        duration_seconds=28800,  # 8 hours
        step_seconds=120,
        seed=42
    )

    strategies = [
        NaivePersistenceStrategy(),
        SimpleMovingAverageStrategy(),
        ExponentialMovingAverageStrategy(alpha=0.15),
    ]

    runner = ValidatorBenchmarkRunner(
        horizon_seconds=3600,
        rolling_step_seconds=1800,
        warmup_seconds=3600
    )

    comparison = runner.run_benchmark(strategies=strategies, dataset=dataset)
    return comparison.model_dump()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
