"""Deterministic documents for phenotype-specific EV population experiments."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from vesiclescope.domain import EVPopulationExperiment, EVPopulationTransport
from vesiclescope.experiment_files import (
    deserialize_experiment_document,
    serialize_experiment_document,
)


POPULATION_EXPERIMENT_SCHEMA = "vesiclescope.population-experiment"
POPULATION_EXPERIMENT_VERSION = 1


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def serialize_population_experiment_document(
    experiment: EVPopulationExperiment,
) -> str:
    if not isinstance(experiment, EVPopulationExperiment):
        raise TypeError("experiment must be an EVPopulationExperiment")
    payload = {
        "experiment_id": experiment.experiment_id,
        "populations": [
            {
                "population_id": population.population_id,
                "phenotype_id": population.phenotype_id,
                "transport_document": json.loads(
                    serialize_experiment_document(population.transport)
                ),
            }
            for population in experiment.populations
        ],
    }
    document = {
        "schema": POPULATION_EXPERIMENT_SCHEMA,
        "version": POPULATION_EXPERIMENT_VERSION,
        "payload_sha256": _digest(payload),
        "payload": payload,
    }
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def deserialize_population_experiment_document(
    text: str,
) -> EVPopulationExperiment:
    if not isinstance(text, str):
        raise TypeError("population experiment document must be text")
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("population experiment document is not valid JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("population experiment document must be an object")
    if document.get("schema") != POPULATION_EXPERIMENT_SCHEMA:
        raise ValueError("unsupported population experiment schema")
    if document.get("version") != POPULATION_EXPERIMENT_VERSION:
        raise ValueError("unsupported population experiment version")

    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("population experiment payload must be an object")
    if document.get("payload_sha256") != _digest(payload):
        raise ValueError("population experiment payload digest mismatch")

    try:
        entries = payload["populations"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("populations must be a non-empty array")
        populations = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("population entry must be an object")
            transport_text = json.dumps(
                entry["transport_document"],
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
            populations.append(
                EVPopulationTransport(
                    population_id=entry["population_id"],
                    phenotype_id=entry["phenotype_id"],
                    transport=deserialize_experiment_document(transport_text),
                )
            )
        return EVPopulationExperiment(
            experiment_id=payload["experiment_id"],
            populations=tuple(populations),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid population experiment: {exc}") from exc
