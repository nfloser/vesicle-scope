"""Curated, source-linked EV evidence database.

The database is a reviewed JSON registry shipped with the package
(``vesiclescope/evidence/data``). Each record is either a *quantity* (a value
or range with unit, context and source) or an *effect* (a stimulus with an
observed direction on an EV outcome). Records paraphrase their sources; they
never copy text, data tables or figures.

The JSON files are the reviewable source of truth. ``export_sqlite`` writes a
derived SQLite file for ad-hoc querying.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

from vesiclescope.domain import (
    EffectDirection,
    EffectOutcome,
    EvidenceCategory,
    EvidenceSource,
    ParameterContext,
    ScientificParameter,
)


SOURCES_SCHEMA = "vesiclescope.evidence-sources"
RECORDS_SCHEMA = "vesiclescope.evidence-records"
_CONTEXT_FIELDS = (
    "species",
    "tissue",
    "cell_type",
    "cell_line",
    "ev_preparation",
    "measurement_method",
    "experimental_conditions",
)


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    title: str
    authors: str
    journal: str | None
    year: int | None
    doi: str | None
    pmid: str | None
    pmcid: str | None
    url: str | None
    peer_reviewed: bool

    @property
    def identifier(self) -> str:
        """Most durable identifier available."""

        if self.doi:
            return f"doi:{self.doi}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        if self.pmcid:
            return f"pmcid:{self.pmcid}"
        return str(self.url)


@dataclass(frozen=True, slots=True)
class QuantityValue:
    central: float | None = None
    sd: float | None = None
    low: float | None = None
    high: float | None = None

    def __post_init__(self) -> None:
        for name in ("central", "sd", "low", "high"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not math.isfinite(float(value))):
                raise ValueError(f"{name} must be a finite number")
        if self.central is None and (self.low is None or self.high is None):
            raise ValueError("a quantity needs a central value or both low and high")
        if (self.low is None) != (self.high is None):
            raise ValueError("low and high must be given together")
        if self.low is not None and self.low > self.high:
            raise ValueError("low must not exceed high")
        if self.sd is not None and (self.sd < 0.0 or self.central is None):
            raise ValueError("sd must be non-negative and accompany a central value")

    def interval(self, *, sd_multiplier: float = 2.0) -> tuple[float, float]:
        """Plausible interval: [low, high], central ± k·sd, or a point."""

        if self.low is not None:
            return (float(self.low), float(self.high))
        if self.sd is not None:
            return (
                max(0.0, self.central - sd_multiplier * self.sd),
                self.central + sd_multiplier * self.sd,
            )
        return (float(self.central), float(self.central))


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    id: str
    kind: str
    evidence: EvidenceCategory
    source: Source
    locator: str
    verification: str
    context: ParameterContext
    statement: str
    limitations: tuple[str, ...]
    tags: tuple[str, ...]
    quantity: str | None = None
    value: QuantityValue | None = None
    unit: str | None = None
    stimulus: dict[str, Any] = field(default_factory=dict)
    outcome: EffectOutcome | None = None
    direction: EffectDirection | None = None
    magnitude: dict[str, Any] | None = None
    time_course: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def evidence_source(self) -> EvidenceSource:
        return EvidenceSource(identifier=self.source.identifier, location=self.locator)

    def to_scientific_parameter(self, identifier: str) -> ScientificParameter:
        """Provenance-complete parameter for a quantity record with a central value."""

        if self.kind != "quantity" or self.value is None or self.value.central is None:
            raise ValueError(f"record {self.id!r} has no central quantity value")
        return ScientificParameter(
            identifier=identifier,
            scientific_name=self.quantity.replace("_", " "),
            value=self.value.central,
            unit=self.unit,
            evidence=self.evidence,
            source=self.evidence_source(),
            context=self.context,
            limitations=self.limitations,
        )


@dataclass(frozen=True, slots=True)
class EvidenceDatabase:
    sources: dict[str, Source]
    records: tuple[EvidenceRecord, ...]
    checked_on: str

    def get(self, record_id: str) -> EvidenceRecord:
        for record in self.records:
            if record.id == record_id:
                return record
        raise KeyError(record_id)

    def quantities(
        self,
        quantity: str | None = None,
        *,
        tag: str | None = None,
        species: str | None = None,
    ) -> tuple[EvidenceRecord, ...]:
        return tuple(
            record
            for record in self.records
            if record.kind == "quantity"
            and (quantity is None or record.quantity == quantity)
            and (tag is None or tag in record.tags)
            and (species is None or (record.context.species or "").startswith(species))
        )

    def effects(
        self,
        *,
        stimulus: str | None = None,
        outcome: EffectOutcome | None = None,
        tag: str | None = None,
    ) -> tuple[EvidenceRecord, ...]:
        needle = stimulus.lower() if stimulus else None
        return tuple(
            record
            for record in self.records
            if record.kind == "effect"
            and (needle is None or needle in str(record.stimulus.get("name", "")).lower()
                 or needle in record.tags)
            and (outcome is None or record.outcome is outcome)
            and (tag is None or tag in record.tags)
        )


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-blank string")
    return value.strip()


def _parse_source(item: dict[str, Any]) -> Source:
    source = Source(
        id=_text(item["id"], "source id"),
        title=_text(item["title"], "source title"),
        authors=_text(item["authors"], "source authors"),
        journal=item.get("journal"),
        year=item.get("year"),
        doi=item.get("doi"),
        pmid=item.get("pmid"),
        pmcid=item.get("pmcid"),
        url=item.get("url"),
        peer_reviewed=bool(item["peer_reviewed"]),
    )
    if not any((source.doi, source.pmid, source.pmcid, source.url)):
        raise ValueError(f"source {source.id!r} needs a DOI, PMID, PMCID or URL")
    return source


def _parse_record(item: dict[str, Any], sources: dict[str, Source]) -> EvidenceRecord:
    record_id = _text(item["id"], "record id")
    kind = item["kind"]
    if kind not in ("quantity", "effect"):
        raise ValueError(f"record {record_id!r} has unsupported kind {kind!r}")
    if item["source"] not in sources:
        raise ValueError(f"record {record_id!r} cites unknown source {item['source']!r}")
    source = sources[item["source"]]
    context_values = item.get("context") or {}
    unknown = set(context_values) - set(_CONTEXT_FIELDS)
    if unknown:
        raise ValueError(f"record {record_id!r} has unknown context fields {sorted(unknown)}")
    limitations = tuple(_text(x, "limitation") for x in item.get("limitations", ()))
    if not source.peer_reviewed and not any("preprint" in x.lower() for x in limitations):
        raise ValueError(f"record {record_id!r} cites a preprint without saying so")
    common = dict(
        id=record_id,
        kind=kind,
        evidence=EvidenceCategory(item["evidence"]),
        source=source,
        locator=_text(item["locator"], "locator"),
        verification=_text(item["verification"], "verification"),
        context=ParameterContext(**context_values),
        statement=_text(item["statement"], "statement"),
        limitations=limitations,
        tags=tuple(item.get("tags", ())),
    )
    known = {
        "id", "kind", "evidence", "source", "locator", "verification", "context",
        "statement", "limitations", "tags", "quantity", "value", "unit", "stimulus",
        "outcome", "direction", "magnitude", "time_course",
    }
    extra = {key: value for key, value in item.items() if key not in known}
    for secondary in extra.get("secondary_sources", ()):
        if secondary not in sources:
            raise ValueError(f"record {record_id!r} cites unknown secondary source {secondary!r}")
    if kind == "quantity":
        return EvidenceRecord(
            **common,
            quantity=_text(item["quantity"], "quantity"),
            value=QuantityValue(**item["value"]),
            unit=_text(item["unit"], "unit"),
            extra=extra,
        )
    stimulus = item["stimulus"]
    if not isinstance(stimulus, dict) or "name" not in stimulus:
        raise ValueError(f"effect {record_id!r} needs a stimulus name")
    return EvidenceRecord(
        **common,
        stimulus=stimulus,
        outcome=EffectOutcome(item["outcome"]),
        direction=EffectDirection(item["direction"]),
        magnitude=item.get("magnitude"),
        time_course=item.get("time_course"),
        extra=extra,
    )


def _read_json(name: str, directory: Path | None) -> dict[str, Any]:
    if directory is not None:
        return json.loads((Path(directory) / name).read_text(encoding="utf-8"))
    return json.loads(
        resources.files("vesiclescope.evidence").joinpath("data", name).read_text(encoding="utf-8")
    )


def load_evidence(directory: Path | None = None) -> EvidenceDatabase:
    """Load and validate the evidence registry (packaged data by default)."""

    sources_doc = _read_json("sources.json", directory)
    records_doc = _read_json("records.json", directory)
    if sources_doc.get("schema") != SOURCES_SCHEMA or records_doc.get("schema") != RECORDS_SCHEMA:
        raise ValueError("unsupported evidence schema")
    sources: dict[str, Source] = {}
    for item in sources_doc["sources"]:
        source = _parse_source(item)
        if source.id in sources:
            raise ValueError(f"duplicate source id {source.id!r}")
        sources[source.id] = source
    records = []
    seen: set[str] = set()
    for item in records_doc["records"]:
        record = _parse_record(item, sources)
        if record.id in seen:
            raise ValueError(f"duplicate record id {record.id!r}")
        seen.add(record.id)
        records.append(record)
    return EvidenceDatabase(
        sources=sources,
        records=tuple(records),
        checked_on=_text(records_doc["checked_on"], "checked_on"),
    )


def export_sqlite(database: EvidenceDatabase, path: Path) -> Path:
    """Write a derived, queryable SQLite copy of the registry."""

    path = Path(path)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE sources (
                id TEXT PRIMARY KEY, title TEXT, authors TEXT, journal TEXT, year INTEGER,
                doi TEXT, pmid TEXT, pmcid TEXT, url TEXT, peer_reviewed INTEGER
            );
            CREATE TABLE records (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, evidence TEXT NOT NULL,
                source_id TEXT NOT NULL REFERENCES sources(id), locator TEXT, verification TEXT,
                statement TEXT, quantity TEXT, unit TEXT, value_central REAL, value_sd REAL,
                value_low REAL, value_high REAL, stimulus TEXT, outcome TEXT, direction TEXT,
                time_course TEXT, species TEXT, cell_type TEXT, cell_line TEXT,
                context_json TEXT, limitations_json TEXT, tags_json TEXT, extra_json TEXT
            );
            """
        )
        for source in database.sources.values():
            connection.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?)",
                (source.id, source.title, source.authors, source.journal, source.year,
                 source.doi, source.pmid, source.pmcid, source.url, int(source.peer_reviewed)),
            )
        for record in database.records:
            value = record.value or QuantityValue(central=0.0)
            context = {name: getattr(record.context, name) for name in _CONTEXT_FIELDS}
            connection.execute(
                "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.id, record.kind, record.evidence.value, record.source.id,
                    record.locator, record.verification, record.statement, record.quantity,
                    record.unit,
                    value.central if record.value else None,
                    value.sd if record.value else None,
                    value.low if record.value else None,
                    value.high if record.value else None,
                    record.stimulus.get("name") if record.stimulus else None,
                    record.outcome.value if record.outcome else None,
                    record.direction.value if record.direction else None,
                    record.time_course, record.context.species, record.context.cell_type,
                    record.context.cell_line, json.dumps(context, sort_keys=True),
                    json.dumps(list(record.limitations)), json.dumps(list(record.tags)),
                    json.dumps(record.extra, sort_keys=True),
                ),
            )
        connection.commit()
    finally:
        connection.close()
    return path


__all__ = [
    "EvidenceDatabase",
    "EvidenceRecord",
    "QuantityValue",
    "Source",
    "export_sqlite",
    "load_evidence",
]
