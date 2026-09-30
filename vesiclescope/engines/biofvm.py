"""Minimal headless adapter for the pinned BioFVM transport runner."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import subprocess

from vesiclescope.domain import BoundaryCondition, TransportExperiment


_PIN_FILE = Path(__file__).with_name("physicell.env")
_PIN_KEYS = frozenset({"PHYSICELL_RELEASE", "PHYSICELL_COMMIT", "BIOFVM_VERSION"})
_RESULT_HEADER = "VESICLESCOPE_BIOFVM_RESULT\t1"


class BioFVMRunError(RuntimeError):
    """Raised when the native BioFVM runner cannot complete successfully."""


def _positive_finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{field_name} must be finite and greater than zero")
    return numeric


def _finite(value: str, field_name: str) -> float:
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name} must be finite")
    return numeric


def _format_number(value: float) -> str:
    numeric = float(value)
    if numeric == 0.0:
        return "0"
    text_value = repr(numeric)
    return text_value[:-2] if text_value.endswith(".0") else text_value


def _is_integer_multiple(total: float, step: float) -> bool:
    ratio = total / step
    return math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1e-9)


def _expected_sample_times(experiment: TransportExperiment) -> tuple[float, ...]:
    count = int(math.floor(experiment.duration_min / experiment.sample_every_min))
    times = [0.0]
    for index in range(1, count + 1):
        time = index * experiment.sample_every_min
        if time < experiment.duration_min and not math.isclose(
            time,
            experiment.duration_min,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            times.append(time)
    if not math.isclose(times[-1], experiment.duration_min, rel_tol=0.0, abs_tol=1e-9):
        times.append(experiment.duration_min)
    return tuple(times)


@dataclass(frozen=True, slots=True)
class BioFVMEngineMetadata:
    """Exact upstream engine identity attached to normalized run results."""

    engine: str
    physicell_release: str
    physicell_commit: str
    biofvm_version: str


def pinned_engine_metadata() -> BioFVMEngineMetadata:
    """Load the single reviewed PhysiCell/BioFVM pin used by build and runtime."""

    values: dict[str, str] = {}
    try:
        lines = _PIN_FILE.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"cannot read BioFVM pin metadata: {_PIN_FILE}") from exc

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise RuntimeError(f"invalid BioFVM pin line: {line!r}")
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in values or not key or not value:
            raise RuntimeError("BioFVM pin metadata contains a duplicate or blank entry")
        values[key] = value

    if set(values) != _PIN_KEYS:
        missing = sorted(_PIN_KEYS - set(values))
        extra = sorted(set(values) - _PIN_KEYS)
        raise RuntimeError(
            f"BioFVM pin metadata keys do not match contract; missing={missing}, extra={extra}"
        )

    return BioFVMEngineMetadata(
        engine="BioFVM",
        physicell_release=values["PHYSICELL_RELEASE"],
        physicell_commit=values["PHYSICELL_COMMIT"],
        biofvm_version=values["BIOFVM_VERSION"],
    )


@dataclass(frozen=True, slots=True)
class BioFVMNumerics:
    """Numerical settings that are solver configuration, not biological inputs."""

    grid_spacing_micron: float
    time_step_min: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "grid_spacing_micron",
            _positive_finite(self.grid_spacing_micron, "grid_spacing_micron"),
        )
        object.__setattr__(
            self,
            "time_step_min",
            _positive_finite(self.time_step_min, "time_step_min"),
        )


@dataclass(frozen=True, slots=True)
class TransportSample:
    """Normalized spatial summary at one requested simulation time."""

    time_min: float
    mean_concentration: float
    min_concentration: float
    max_concentration: float

    def __post_init__(self) -> None:
        values = (
            self.time_min,
            self.mean_concentration,
            self.min_concentration,
            self.max_concentration,
        )
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            raise TypeError("transport sample values must be real numbers")
        numeric = tuple(float(value) for value in values)
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("transport sample values must be finite")
        if numeric[0] < 0.0:
            raise ValueError("sample time must be non-negative")

        mean = numeric[1]
        minimum = numeric[2]
        maximum = numeric[3]
        if minimum > maximum:
            raise ValueError("sample minimum cannot exceed maximum")
        if mean < minimum:
            if not math.isclose(mean, minimum, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("sample minimum, mean and maximum are inconsistent")
            mean = minimum
        elif mean > maximum:
            if not math.isclose(mean, maximum, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("sample minimum, mean and maximum are inconsistent")
            mean = maximum

        object.__setattr__(self, "time_min", numeric[0])
        object.__setattr__(self, "mean_concentration", mean)
        object.__setattr__(self, "min_concentration", minimum)
        object.__setattr__(self, "max_concentration", maximum)


@dataclass(frozen=True, slots=True)
class BioFVMRunResult:
    """Engine-neutral identity plus normalized summary samples."""

    experiment_id: str
    concentration_unit: str
    engine: BioFVMEngineMetadata
    samples: tuple[TransportSample, ...]


def _validate_mapping(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
) -> None:
    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(numerics, BioFVMNumerics):
        raise TypeError("numerics must be BioFVMNumerics")
    if experiment.boundary is not BoundaryCondition.NO_FLUX:
        raise ValueError(f"unsupported BioFVM boundary: {experiment.boundary!r}")

    grid = numerics.grid_spacing_micron
    if not _is_integer_multiple(experiment.domain.width_micron, grid):
        raise ValueError("grid spacing must tile domain width exactly")
    if not _is_integer_multiple(experiment.domain.height_micron, grid):
        raise ValueError("grid spacing must tile domain height exactly")

    dt = numerics.time_step_min
    if not _is_integer_multiple(experiment.duration_min, dt):
        raise ValueError("time step must tile experiment duration exactly")
    if not _is_integer_multiple(experiment.sample_every_min, dt):
        raise ValueError("time step must tile sample interval exactly")


def build_command(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
    executable: Path,
) -> tuple[str, ...]:
    """Map a validated transport contract to the native runner command."""

    _validate_mapping(experiment, numerics)
    executable_path = Path(executable)
    if not str(executable_path):
        raise ValueError("executable path must not be blank")

    return (
        str(executable_path),
        "--width-micron",
        _format_number(experiment.domain.width_micron),
        "--height-micron",
        _format_number(experiment.domain.height_micron),
        "--duration-min",
        _format_number(experiment.duration_min),
        "--sample-every-min",
        _format_number(experiment.sample_every_min),
        "--boundary",
        experiment.boundary.value,
        "--diffusion-micron2-per-min",
        _format_number(experiment.diffusion.value),
        "--decay-per-min",
        _format_number(experiment.decay.value),
        "--initial-concentration",
        _format_number(experiment.initial_concentration.value),
        "--concentration-unit",
        experiment.initial_concentration.unit,
        "--grid-spacing-micron",
        _format_number(numerics.grid_spacing_micron),
        "--time-step-min",
        _format_number(numerics.time_step_min),
    )


def parse_result(
    experiment: TransportExperiment,
    stdout: str,
) -> BioFVMRunResult:
    """Parse and validate the native runner's deliberately small TSV contract."""

    if not isinstance(experiment, TransportExperiment):
        raise TypeError("experiment must be a TransportExperiment")
    if not isinstance(stdout, str):
        raise TypeError("stdout must be text")

    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines or lines[0] != _RESULT_HEADER:
        raise ValueError("BioFVM result header is missing or unsupported")

    metadata: dict[str, str] = {}
    samples: list[TransportSample] = []

    for line in lines[1:]:
        fields = line.split("\t")
        if fields[0] == "sample":
            if len(fields) != 5:
                raise ValueError(f"invalid BioFVM sample line: {line!r}")
            samples.append(
                TransportSample(
                    time_min=_finite(fields[1], "sample time"),
                    mean_concentration=_finite(fields[2], "sample mean"),
                    min_concentration=_finite(fields[3], "sample minimum"),
                    max_concentration=_finite(fields[4], "sample maximum"),
                )
            )
            continue

        if len(fields) != 2 or fields[0] not in {
            "engine",
            "physicell_release",
            "physicell_commit",
            "biofvm_version",
        }:
            raise ValueError(f"invalid BioFVM metadata line: {line!r}")
        if fields[0] in metadata:
            raise ValueError(f"duplicate BioFVM metadata field: {fields[0]}")
        metadata[fields[0]] = fields[1]

    expected = pinned_engine_metadata()
    observed = BioFVMEngineMetadata(
        engine=metadata.get("engine", ""),
        physicell_release=metadata.get("physicell_release", ""),
        physicell_commit=metadata.get("physicell_commit", ""),
        biofvm_version=metadata.get("biofvm_version", ""),
    )
    if observed != expected:
        raise ValueError(
            f"BioFVM engine metadata does not match the reviewed pin: {observed!r}"
        )

    if not samples:
        raise ValueError("BioFVM result contains no samples")
    for previous, current in zip(samples, samples[1:]):
        if current.time_min <= previous.time_min:
            raise ValueError("BioFVM sample times must be strictly increasing")

    expected_times = _expected_sample_times(experiment)
    observed_times = tuple(sample.time_min for sample in samples)
    if len(observed_times) != len(expected_times) or any(
        not math.isclose(observed_time, expected_time, rel_tol=0.0, abs_tol=1e-9)
        for observed_time, expected_time in zip(observed_times, expected_times)
    ):
        raise ValueError(
            f"BioFVM sample times do not match requested output: "
            f"expected={expected_times}, observed={observed_times}"
        )

    return BioFVMRunResult(
        experiment_id=experiment.experiment_id,
        concentration_unit=experiment.initial_concentration.unit,
        engine=observed,
        samples=tuple(samples),
    )


def run_transport(
    experiment: TransportExperiment,
    numerics: BioFVMNumerics,
    executable: Path,
) -> BioFVMRunResult:
    """Run the pinned native BioFVM executable without invoking a shell."""

    command = build_command(experiment, numerics, executable)
    try:
        completed = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", None)
        detail = str(stderr).strip() if stderr else str(exc)
        raise BioFVMRunError(f"BioFVM transport run failed: {detail}") from exc

    return parse_result(experiment, completed.stdout)
