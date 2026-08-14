"""Coordination run endpoints: trigger a coordination cycle against
persisted state, and retrieve a previously persisted run.

Handlers stay thin — they assemble the engine's input from persisted
state via the repository, call the existing deterministic
``run_coordination`` engine unchanged, and persist the result. No
coordination/decision logic lives here.

After a run is persisted, its result is also broadcast to connected
WebSocket clients (Milestone 6) via ``broadcast_threadsafe`` — this
handler is a plain ``def``, so FastAPI runs it in a worker thread, not
the asyncio event loop, which is exactly the case
``broadcast_threadsafe`` is for. Broadcasting is a realtime notification
of the decision already made and saved above; it is not part of the
coordination decision itself.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.schemas import CoordinationRunCreate
from app.coordination import run_coordination
from app.db import repository as repo
from app.domain import CoordinationRun
from app.realtime import coordination_completed_event, manager

router = APIRouter(prefix="/coordination", tags=["coordination"])


@router.post("/runs", response_model=CoordinationRun, status_code=status.HTTP_201_CREATED)
def create_coordination_run(payload: CoordinationRunCreate, db: DbSession) -> CoordinationRun:
    context = repo.build_coordination_context(db, trigger_reason=payload.trigger_reason)
    run = run_coordination(context)
    saved = repo.save_coordination_run(db, run)
    manager.broadcast_threadsafe(coordination_completed_event(saved))
    return saved


@router.get("/runs/{run_id}", response_model=CoordinationRun)
def get_coordination_run(run_id: str, db: DbSession) -> CoordinationRun:
    run = repo.get_coordination_run(db, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"coordination run '{run_id}' not found")
    return run
