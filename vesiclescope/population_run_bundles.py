"""Durable bundles for independent EV phenotype-population runs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from vesiclescope.domain import EVPopulationExperiment, EVPopulationTransport
from vesiclescope.engines import BioFVMNumerics
from vesiclescope.run_bundles import (
    SimulationRunBundle,
    deserialize_run_bundle,
    serialize_run_bundle,
)
from vesiclescope.workflows.population_transport import (
    EVPopulationRunResult,
    PopulationTransportResult,
)


POPULATION_RUN_BUNDLE_SCHEMA = "vesiclescope.population-simulation-run"
POPULATION_RUN_BUNDLE_VERSION = 1


@dataclass(frozen=True, slots=True)
class PopulationSimulationRunBundle:
    """One reproducible independent-population composition run."""

    vesiclescope_revision: str
    experiment: EVPopulationExperiment
    numerics: BioFVMNumerics
    result: EVPopulationRunResult

    def __post_init__(self) -> None:
        if not isinstance(self.vesiclescope_revision, str) or not self.vesiclescope_revision.strip():
            raise ValueError("vesiclescope_revision must be non-blank")
        if not isinstance(self.experiment, EVPopulationExperiment):
            raise TypeError("experiment must be an EVPopulationExperiment")
        if not isinstance(self.numerics, BioFVMNumerics):
            raise TypeError("numerics must be BioFVMNumerics")
        if not isinstance(self.result, EVPopulationRunResult):
            raise TypeError("result must be an EVPopulationRunResult")
        if self.result.experiment_id != self.experiment.experiment_id:
            raise ValueError("population result experiment_id does not match experiment")
        expected = tuple(
            (p.population_id, p.phenotype_id, p.transport.experiment_id)
            for p in self.experiment.populations
        )
        observed = tuple(
            (p.population_id, p.phenotype_id, p.result.experiment_id)
            for p in self.result.populations
        )
        if observed != expected:
            raise ValueError("population results must match configured populations")


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


def _payload(bundle: PopulationSimulationRunBundle) -> dict[str, Any]:
    population_runs = []
    for population, result in zip(
        bundle.experiment.populations,
        bundle.result.populations,
    ):
        inner = SimulationRunBundle(
            vesiclescope_revision=bundle.vesiclescope_revision,
            experiment=population.transport,
            numerics=bundle.numerics,
            result=result.result,
        )
        population_runs.append(
            {
                "population_id": population.population_id,
                "phenotype_id": population.phenotype_id,
                "run_bundle": json.loads(serialize_run_bundle(inner).decode("utf-8")),
            }
        )
    return {
        "vesiclescope_revision": bundle.vesiclescope_revision,
        "experiment_id": bundle.experiment.experiment_id,
        "population_runs": population_runs,
    }


def serialize_population_run_bundle(
    bundle: PopulationSimulationRunBundle,
) -> bytes:
    if not isinstance(bundle, PopulationSimulationRunBundle):
        raise TypeError("bundle must be a PopulationSimulationRunBundle")
    payload = _payload(bundle)
    document = {
        "schema": POPULATION_RUN_BUNDLE_SCHEMA,
        "version": POPULATION_RUN_BUNDLE_VERSION,
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
    ).encode("utf-8")


def deserialize_population_run_bundle(
    data: bytes | str,
) -> PopulationSimulationRunBundle:
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("population run bundle must be UTF-8") from exc
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("population run bundle must be bytes or text")

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("population run bundle contains malformed JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("population run bundle must be an object")
    if document.get("schema") != POPULATION_RUN_BUNDLE_SCHEMA:
        raise ValueError("unsupported population run bundle schema")
    if document.get("version") != POPULATION_RUN_BUNDLE_VERSION:
        raise ValueError("unsupported population run bundle version")
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("population run bundle payload must be an object")
    if document.get("payload_sha256") != _digest(payload):
        raise ValueError("population run bundle payload digest mismatch")

    try:
        population_entries = payload["population_runs"]
        if not isinstance(population_entries, list) or not population_entries:
            raise ValueError("population_runs must be a non-empty array")

        population_specs = []
        population_results = []
        numerics = None
        revision = payload["vesiclescope_revision"]
        for entry in population_entries:
            if not isinstance(entry, dict):
                raise ValueError("population run entry must be an object")
            inner_text = json.dumps(
                entry["run_bundle"],
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
            inner = deserialize_run_bundle(inner_text)
            if inner.vesiclescope_revision != revision:
                raise ValueError("nested run bundle revision does not match population bundle")
            if numerics is None:
                numerics = inner.numerics
            elif inner.numerics != numerics:
                raise ValueError("nested population runs must share numerical settings")
            population_specs.append(
                EVPopulationTransport(
                    population_id=entry["population_id"],
                    phenotype_id=entry["phenotype_id"],
                    transport=inner.experiment,
                )
            )
            population_results.append(
                PopulationTransportResult(
                    population_id=entry["population_id"],
                    phenotype_id=entry["phenotype_id"],
                    result=inner.result,
                )
            )

        experiment = EVPopulationExperiment(
            experiment_id=payload["experiment_id"],
            populations=tuple(population_specs),
        )
        result = EVPopulationRunResult(
            experiment_id=payload["experiment_id"],
            populations=tuple(population_results),
        )
        if numerics is None:
            raise ValueError("population run bundle is empty")
        return PopulationSimulationRunBundle(
            vesiclescope_revision=revision,
            experiment=experiment,
            numerics=numerics,
            result=result,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid population run bundle: {exc}") from exc


def write_population_run_bundle(
    path: Path,
    bundle: PopulationSimulationRunBundle,
) -> Path:
    output = Path(path)
    if output.exists() and output.is_dir():
        raise ValueError("population run bundle output path must be a file")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = serialize_population_run_bundle(bundle)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, output)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return output


def read_population_run_bundle(path: Path) -> PopulationSimulationRunBundle:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read population run bundle: {source}") from exc
    return deserialize_population_run_bundle(data)
