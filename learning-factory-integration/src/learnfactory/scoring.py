from __future__ import annotations

from typing import Mapping


DEFAULT_WEIGHTS = {
    "expected_future_learning_value": 2.0,
    "future_regeneration_cost": 1.5,
    "production_relevance": 1.4,
    "systems_depth": 1.4,
    "curriculum_importance": 1.2,
    "source_availability": 0.8,
    "prerequisite_value": 1.0,
    "artifact_uniqueness": 1.0,
    "agent_compute_cost": -0.4,
}


def priority_score(features: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    """Pragmatic, configurable score on roughly 0-10 normalized features."""
    selected = dict(DEFAULT_WEIGHTS)
    if weights:
        selected.update(weights)
    return round(sum(selected.get(name, 0.0) * float(value) for name, value in features.items()), 4)
