"""Coordination engine: the core decision-making module of EnerFabric.

Given current state, asset capabilities, active intents, system
policies and grid state, produces a feasible, explainable multi-asset
allocation plan.

Deterministic, constraint-aware, explainable, testable, and free of any
ML dependency for the core decision path. See ``engine.py`` for the
algorithm and ``context.py``/``constraints.py`` for its inputs and rule
lookups.
"""

from app.coordination.context import CoordinationContext
from app.coordination.engine import run_coordination

__all__ = ["CoordinationContext", "run_coordination"]
