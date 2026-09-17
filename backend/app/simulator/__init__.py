"""Deterministic DER simulator: solar, battery, EV charger, flexible load,
critical load, and grid.

Behaves like external device infrastructure (publishing over MQTT) rather
than mutating internal application state directly, so that simulated
DERs can later be replaced by real device adapters without changing the
coordination engine or API. Implemented in Milestone 3.
"""
