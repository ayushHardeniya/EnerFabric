# The Coordination Engine

> Physical connectivity does not solve system-level coordination.

A site's solar inverter, battery, EV charger, and load controllers are
usually already "connected" — each reports its own state to its own
app or cloud service. That doesn't answer the question that actually
matters: **given everything happening on the site right now, what
should each asset do next, and why?**

That's what the Coordination Engine answers. It is the reason
EnerFabric exists as a separate layer rather than just a dashboard on
top of existing device connectivity.

## Decision flow

```
Intent
  ↓
Policies / Priorities / Constraints
  ↓
Current DER State (telemetry)
  ↓
Coordination Engine
  ↓
Allocation
  ↓
Explanation
```

- **Intent** — what an asset needs or prefers: an EV's
  `TargetSocByDeadlineIntent` ("80% by 7am"), a battery's
  `MinimumReserveIntent` ("keep at least 30%"), a critical load's
  `MinimumSupplyIntent`, a deferrable load's `DeferrableIntent`, or a
  site-level `PreferRenewableIntent`.
- **Policies / priorities / constraints** — system-wide rules:
  protect critical loads, maintain battery reserve, limit grid import,
  reduce peak demand, prefer renewable energy — each with its own
  priority and (where relevant) a threshold.
- **Current DER state** — each asset's live telemetry: power, state of
  charge, availability.
- **Coordination Engine** — combines all three into a feasible,
  multi-asset allocation plan for this cycle.
- **Allocation** — a per-asset action (`charge`, `discharge`,
  `consume`, `generate`, `curtail`, `defer`, `hold`), a power level,
  and a `feasible` flag.
- **Explanation** — every allocation carries a required, non-blank
  `reason`. Nothing is decided silently.

Source: [`backend/app/coordination/`](../backend/app/coordination/)
(`context.py`, `constraints.py`, `engine.py`); scenario-level tests in
[`backend/tests/coordination/test_scenarios.py`](../backend/tests/coordination/test_scenarios.py).

## What the engine actually does

`run_coordination(context) -> CoordinationRun` is a pure, synchronous
function — no I/O, no randomness, no hidden state. The same input
snapshot always produces the same decision. Internally it runs a fixed
sequence of allocation passes that all compete for the same shared
solar-surplus and grid-import budget, rather than deciding each asset
in isolation:

1. **Critical loads first** — sourced solar → battery discharge (if
   above reserve) → grid, unconditionally, before anything else.
2. **Battery reserve is a hard gate**, not a soft target — at or below
   its configured floor, a battery's discharge capacity for the cycle
   is 0.
3. **Battery charging only draws from solar surplus**, never the grid
   — "prefer renewable" is structural, not a bolt-on rule.
4. **The grid import limit throttles EV charging and flexible loads
   only** — critical load may still push net import over the limit if
   that's the only way to serve it, and the resulting grid allocation
   is explicitly marked infeasible with the reason, rather than
   silently exceeding the constraint without saying so.
5. **EV chargers and flexible loads are ordered by priority, then
   asset id**, before allocation — this is how competing intents for
   the same limited solar/grid capacity are resolved, deterministically.
6. **A grid asset must exist and be available** for its budget to
   count as usable capacity — no grid asset means zero grid headroom,
   never an unlimited phantom source.

This is priority- and constraint-based dispatch, not machine learning
and not mathematical optimization — a deliberate MVP choice (see
`CLAUDE.md` §9/§10) that keeps every decision traceable to a specific
rule.

## A concrete example

Given: solar generation, a battery above its reserve floor, an EV with
a `TargetSocByDeadlineIntent`, and an available grid — the engine
produces a feasible `charge` allocation for the EV at its charger's
capability-limited rate, sourced from solar surplus plus grid headroom,
with a reason naming the exact power and source mix, plus a
deadline-achievability note ("on track" / "may not be reached")
computed from the EV's remaining capacity and time.

If solar is low, grid demand is high, and the battery is needed for
critical-load protection, the same EV intent instead produces a
`hold`/deferred allocation with a reason such as:

> "EV charging deferred because solar availability is low, grid demand
> is high, battery reserve must be protected, the EV deadline is still
> achievable, and EV priority is medium."

Same inputs, same engine, two different — and both explainable —
outcomes.

## What this is not

- Not an ML predictor — no model, no training data, no probabilistic
  output.
- Not a power-flow simulation — it reasons over declared capabilities
  and telemetry, not electrical network physics.
- Not a market/trading system — no pricing or bidding logic.
- Not a general-purpose optimizer — no OR-Tools or LP solver is in the
  decision path today (`CLAUDE.md` §9 keeps that as an option only if
  it materially improves the MVP; it hasn't been needed).

## Known, documented simplifications

- Battery reserve is a binary SOC gate for the current cycle, not an
  energy-integrated (kWh-over-time) reduction.
- Battery discharge is used for critical-load shortfall only, not as a
  general relief valve for EV/flexible-load grid pressure.
- Deadline feasibility is a single-cycle average-power estimate, not a
  multi-cycle simulation.
- The Impact Engine (quantifying the outcome of a decision — grid
  import reduction, renewable utilization, etc.) is not implemented;
  `CoordinationRun.impact` is always `null` today.
