"""
AEGIS Cross-Oracle Risk Layer API Service.
FastAPI REST server implementing endpoints for multi-oracle consensus, risk resolution, and protocol simulation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
try:
    from services.api.src.models.schema import (
        SimulationResetRequest,
        SimulationStepRequest,
        SimulationConfigRequest,
        PositionUpdateRequest,
    )
    from services.api.src.core.simulation_engine import SimulationEngine
except ImportError:
    from src.models.schema import (
        SimulationResetRequest,
        SimulationStepRequest,
        SimulationConfigRequest,
    )
    from src.core.simulation_engine import SimulationEngine

app = FastAPI(
    title="AEGIS — Cross-Oracle Risk Engine API",
    description="On-Chain Oracle Cross-Checking & Risk-Resolution Layer.",
    version="0.2.0-mvp",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulation_engine = SimulationEngine()


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "AEGIS Cross-Oracle Risk Engine",
        "version": "0.2.0-mvp",
        "supported_oracles": ["Multipli OSM", "Chainlink", "Pyth", "Chronicle", "RedStone", "Supra", "API3"],
    }


@app.get("/api/scenarios")
def list_scenarios():
    """List all available deterministic cross-oracle test scenarios."""
    return [
        {
            "scenario_id": "scen_normal",
            "title": "Normal Market Convergence",
            "description": "Multipli OSM and all external oracle feeds agree in tight consensus (~$4,320/oz). Standard 80% LTV.",
            "category": "NORMAL",
            "p_osm_initial": 4320.0,
            "expected_market": 4320.0,
            "asset": "Tokenized Gold (XAU/USD)",
            "ltv_default": 0.80,
        },
        {
            "scenario_id": "scen_flash_crash",
            "title": "Multipli OSM Divergence / Market Drop (Hero Demo)",
            "description": "External spot market falls to ~$4,050 while Multipli OSM remains delayed at $4,380. AEGIS detects divergence and restricts LTV.",
            "category": "MULTIPLI_DEVIATION",
            "p_osm_initial": 4380.0,
            "expected_market": 4050.0,
            "asset": "Tokenized Gold (XAU/USD)",
            "ltv_default": 0.80,
        },
        {
            "scenario_id": "scen_outlier",
            "title": "Single Oracle Outlier Rejection",
            "description": "A single oracle feed reports an anomalous $9,000 quote. Agreement clustering isolates the outlier and preserves consensus.",
            "category": "OUTLIER",
            "p_osm_initial": 4050.0,
            "expected_market": 4050.0,
            "asset": "Tokenized Gold (XAU/USD)",
            "ltv_default": 0.80,
        },
        {
            "scenario_id": "scen_disagreement",
            "title": "Multi-Oracle Disagreement (Bimodal Split)",
            "description": "External oracles split into two contradictory clusters ($4,050 vs $4,450). No consensus exists; emergency circuit breaker engages.",
            "category": "DISAGREEMENT",
            "p_osm_initial": 4300.0,
            "expected_market": 4050.0,
            "asset": "Tokenized Gold (XAU/USD)",
            "ltv_default": 0.80,
        },
        {
            "scenario_id": "scen_outage",
            "title": "Source Outage & Staleness Resilience",
            "description": "Two oracle feeds fail/stale out. The system gracefully continues on remaining active quorum (SOURCE_DEGRADED).",
            "category": "OUTAGE",
            "p_osm_initial": 4050.0,
            "expected_market": 4050.0,
            "asset": "Tokenized Gold (XAU/USD)",
            "ltv_default": 0.80,
        },
    ]


@app.get("/api/benchmarks/summary")
def get_benchmarks_summary():
    """Return benchmark summaries."""
    return {
        "benchmark_id": "bench_cross_oracle_v1",
        "status": "SIMULATED",
        "results": [
            {"strategy": "Chainlink Spot Adapter", "mae": 0.04, "latency_ms": 0.42},
            {"strategy": "Pyth Confidence Stream", "mae": 0.03, "latency_ms": 0.18},
            {"strategy": "Chronicle Protocol Feed", "mae": 0.05, "latency_ms": 0.35},
        ],
        "ranked_by_mae": ["Pyth Confidence Stream", "Chainlink Spot Adapter", "Chronicle Protocol Feed"],
    }


@app.post("/api/scenarios/run")
def run_scenario_endpoint(req: dict):
    """Run a scenario evaluation."""
    scen_id = req.get("scenario_id", "scen_normal")
    simulation_engine.reset(scen_id)
    return simulation_engine.get_snapshot()


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
    """Advance simulation clock by delta_seconds."""
    simulation_engine.step(delta_seconds=req.delta_seconds if req.delta_seconds is not None else 600.0)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
