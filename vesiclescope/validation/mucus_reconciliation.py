"""Read-only reconciliation of the reviewed DRUM and Dryad mucus snapshots."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
import math
from pathlib import Path

from vesiclescope.validation.dryad_data import read_verified_dryad_v3_source
from vesiclescope.validation import mucus_data


MEASUREMENT_FILE = 'bEV_diffusion_host_response_CVM_1sMSD.csv'
SUMMARY_FILE = 'bEV_diffusion_host_response_CVM_SampleInfo.csv'
SHORT_SPECIES = ('LC', 'LI', 'GV', 'MM')
REPRESENTATION_REL_TOLERANCE = 1e-12


def _ordered_sequence_relation(
    dryad_count: int,
    drum_count: int,
    representation_difference_count: int,
    substantive_mismatch_count: int,
) -> str:
    if substantive_mismatch_count:
        return 'not_equal_or_prefix'
    qualifier = 'representation_equivalent' if representation_difference_count else 'exact'
    if dryad_count == drum_count:
        return f'{qualifier}_equal'
    if dryad_count < drum_count:
        return f'dryad_is_{qualifier}_prefix_of_drum'
    return f'drum_is_{qualifier}_prefix_of_dryad'


def _csv_rows(raw: bytes, name: str) -> list[list[str]]:
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError(f'{name}: expected UTF-8 CSV') from exc
    try:
        return list(csv.reader(StringIO(text, newline='')))
    except csv.Error as exc:
        raise ValueError(f'{name}: invalid CSV') from exc


def _csv_number(value: str, location: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f'{location}: expected a numeric measurement') from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{location}: measurement must be finite and nonnegative')
    return number


def _dryad_measurements(raw: bytes) -> list[list[float]]:
    rows = _csv_rows(raw, MEASUREMENT_FILE)
    width = 80
    expected_samples = [f'Sample {sample}' for sample in range(1, 11) for _ in range(8)]
    expected_species = list(SHORT_SPECIES) * 20
    expected_particles = (['EV'] * 4 + ['WB'] * 4) * 10
    if len(rows) < 4 or rows[0] != expected_samples or rows[1] != expected_species or rows[2] != expected_particles:
        raise ValueError(f'{MEASUREMENT_FILE}: unexpected three-row column header mapping')
    if any(len(row) > width for row in rows[3:]):
        raise ValueError(f'{MEASUREMENT_FILE}: unexpected populated columns')

    columns: list[list[float]] = []
    for column in range(width):
        values = []
        for row_number, row in enumerate(rows[3:], start=4):
            value = row[column] if column < len(row) else ''
            if value == '':
                continue
            values.append(_csv_number(value, f'{MEASUREMENT_FILE} row {row_number}, column {column + 1}'))
        if not values:
            raise ValueError(f'{MEASUREMENT_FILE} column {column + 1}: empty measurement group')
        columns.append(values)
    return columns


def _dryad_summaries(raw: bytes) -> tuple[list[list[float]], list[list[int]]]:
    rows = _csv_rows(raw, SUMMARY_FILE)
    expected = [
        'Sample Number', 'LC bEVs', 'LI bEVs', 'GV bEVs', 'MM bEVs',
        'LC WB', 'LI WB', 'GV WB', 'MM WB', 'pH',
    ]
    if not rows or rows[0] != expected or len(rows) != 11 or any(len(row) != 10 for row in rows):
        raise ValueError(f'{SUMMARY_FILE}: unexpected row or column mapping')
    summaries = []
    decimal_places = []
    for sample, row in enumerate(rows[1:], start=1):
        values = [_csv_number(value, f'{SUMMARY_FILE} sample {sample}') for value in row]
        if values[0] != sample:
            raise ValueError(f'{SUMMARY_FILE}: sample identity does not match row order')
        summaries.append(values[1:9] + [values[0], values[9]])
        try:
            decimal_places.append([
                max(0, -Decimal(value).as_tuple().exponent)
                for value in row[1:9]
            ])
        except InvalidOperation as exc:
            raise ValueError(f'{SUMMARY_FILE} sample {sample}: invalid decimal representation') from exc
    return summaries, decimal_places


def _geometric_mean(values: list[float]) -> float:
    if any(value == 0 for value in values):
        return 0.0
    return math.exp(math.fsum(math.log(value) for value in values) / len(values))


def _arithmetic_mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def _matches_reported_rounding(mean: float, reported: float, decimal_places: int) -> bool:
    half_unit = 0.5 * (10.0 ** -decimal_places)
    return abs(mean - reported) <= math.nextafter(half_unit, math.inf)


def _residual_in_reported_units(mean: float, reported: float, decimal_places: int) -> float:
    return (mean - reported) / (10.0 ** -decimal_places)


def _cvm_exclusion_provenance(raw_files: dict[str, bytes]) -> dict[str, object]:
    removed_outlier_files = sorted(
        name for name in raw_files if name.endswith('_removed_outliers.csv')
    )
    readme = raw_files['README.md'].decode('utf-8')
    cvm_outlier_files = [name for name in removed_outlier_files if 'CVM' in name]
    return {
        'source': 'verified Dryad v3 inventory and README.md',
        'removed_outlier_file_count': len(removed_outlier_files),
        'removed_outlier_files': removed_outlier_files,
        'readme_lists_all_removed_outlier_files': all(
            name in readme for name in removed_outlier_files
        ),
        'cvm_removed_outlier_file_present': bool(cvm_outlier_files),
        'cvm_filtering_status': 'unknown',
        'primary_methods_source': {
            'doi': '10.1038/s41522-025-00866-9',
            'section': 'Statistical analysis',
        },
        'primary_methods_outlier_scope': [
            'characterization',
            'uptake',
            'viability',
        ],
        'primary_methods_names_multiple_particle_tracking_in_outlier_scope': False,
        'primary_methods_interpretation': (
            'The primary outlier-removal sentence does not name multiple-particle '
            'tracking; that omission narrows the documented scope but does not prove '
            'that the supplied CVM values are unfiltered.'
        ),
        'interpretation': (
            'No separate CVM removed-outlier file is deposited; absence does not establish '
            'that the supplied CVM values are unfiltered.'
        ),
    }


def _drum_snapshot(path: Path) -> tuple[list[list[float]], list[list[float]], str, int, str]:
    raw = Path(path).read_bytes()
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    if digest != mucus_data.REVIEWED_SHA256:
        raise ValueError('workbook SHA-256 does not match the reviewed DRUM original')
    try:
        import openpyxl
    except ImportError as exc:
        raise ValueError("XLSX reconciliation requires the optional reader: pip install 'vesicle-scope[data]'") from exc

    workbook = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    try:
        expected_sheets = ['1s MSD GeoMean'] + [f'Sample {i}' for i in range(1, 11)]
        if workbook.sheetnames != expected_sheets:
            raise ValueError('unexpected sample sheet inventory or order')
        summary_rows = mucus_data._rows(workbook['1s MSD GeoMean'], mucus_data.SUMMARY_HEADERS)
        if len(summary_rows) != 10:
            raise ValueError('summary must contain exactly ten independent samples')
        summaries = []
        columns = []
        for sample, summary in enumerate(summary_rows, start=1):
            parsed_summary = [
                mucus_data._number(value, f'summary row {sample + 1}')
                for value in summary
            ]
            if parsed_summary[8] != sample:
                raise ValueError('summary sample identity does not match the sample sheet')
            summaries.append(parsed_summary)
            sheet = workbook[f'Sample {sample}']
            mucus_data._rows(sheet, mucus_data.PARTICLE_HEADERS)
            rows = list(sheet.iter_rows(min_row=2, max_col=8, values_only=True))
            for column in range(8):
                values = [
                    mucus_data._number(row[column], f'{sheet.title} column {column + 1}')
                    for row in rows if row[column] is not None
                ]
                if not values:
                    raise ValueError(f'{sheet.title} column {column + 1}: empty measurement group')
                columns.append(values)
    finally:
        workbook.close()
    return columns, summaries, digest, len(raw), openpyxl.__version__


def reconcile_mucus_snapshots(workbook_path: Path, dryad_path: Path) -> dict[str, object]:
    """Compare verified snapshots without converting or fitting measurements."""
    raw_files, dryad_container = read_verified_dryad_v3_source(dryad_path)
    dryad_columns = _dryad_measurements(raw_files[MEASUREMENT_FILE])
    dryad_summaries, dryad_summary_places = _dryad_summaries(raw_files[SUMMARY_FILE])
    exclusion_provenance = _cvm_exclusion_provenance(raw_files)
    drum_columns, drum_summaries, drum_digest, drum_size, reader_version = _drum_snapshot(workbook_path)

    group_differences = []
    representation_only = 0
    substantive = 0
    unpaired_drum = 0
    unpaired_dryad = 0
    exact = 0
    for index, (dryad_values, drum_values) in enumerate(zip(dryad_columns, drum_columns)):
        representation = 0
        group_substantive = 0
        group_exact = 0
        for dryad_value, drum_value in zip(dryad_values, drum_values):
            if dryad_value == drum_value:
                group_exact += 1
            elif math.isclose(
                dryad_value,
                drum_value,
                rel_tol=REPRESENTATION_REL_TOLERANCE,
                abs_tol=0.0,
            ):
                representation += 1
            else:
                group_substantive += 1
        group_unpaired_drum = max(0, len(drum_values) - len(dryad_values))
        group_unpaired_dryad = max(0, len(dryad_values) - len(drum_values))
        sequence_relation = _ordered_sequence_relation(
            len(dryad_values),
            len(drum_values),
            representation,
            group_substantive,
        )
        exact += group_exact
        representation_only += representation
        substantive += group_substantive
        unpaired_drum += group_unpaired_drum
        unpaired_dryad += group_unpaired_dryad
        if representation or group_substantive or group_unpaired_drum or group_unpaired_dryad:
            column = index % 8
            group_differences.append({
                'sample_id': index // 8 + 1,
                'species': mucus_data.SPECIES[column % 4],
                'particle_type': 'bEV' if column < 4 else 'whole_bacterium',
                'dryad_count': len(dryad_values),
                'drum_count': len(drum_values),
                'exact_shared_value_count': group_exact,
                'representation_only_difference_count': representation,
                'substantive_value_mismatch_count': group_substantive,
                'unpaired_drum_value_count': group_unpaired_drum,
                'unpaired_dryad_value_count': group_unpaired_dryad,
                'ordered_sequence_relation': sequence_relation,
                'first_unpaired_ordinal': (
                    min(len(dryad_values), len(drum_values)) + 1
                    if len(dryad_values) != len(drum_values)
                    else None
                ),
            })

    summary_mismatches = sum(
        dryad_value != drum_value
        for dryad_row, drum_row in zip(dryad_summaries, drum_summaries)
        for dryad_value, drum_value in zip(dryad_row, drum_row)
    )
    aggregation_results = []
    dryad_rounding_matches = 0
    drum_rounding_matches = 0
    dryad_arithmetic_matches = 0
    drum_arithmetic_matches = 0
    dryad_near_mismatches = 0
    drum_near_mismatches = 0
    comparable_summaries = summary_mismatches == 0
    aggregation_pairs = zip(dryad_columns, drum_columns) if comparable_summaries else ()
    for index, (dryad_values, drum_values) in enumerate(aggregation_pairs):
        sample_index = index // 8
        column = index % 8
        reported = dryad_summaries[sample_index][column]
        places = dryad_summary_places[sample_index][column]
        dryad_geometric_mean = _geometric_mean(dryad_values)
        drum_geometric_mean = _geometric_mean(drum_values)
        dryad_match = _matches_reported_rounding(dryad_geometric_mean, reported, places)
        drum_match = _matches_reported_rounding(drum_geometric_mean, reported, places)
        dryad_residual = _residual_in_reported_units(
            dryad_geometric_mean, reported, places
        )
        drum_residual = _residual_in_reported_units(
            drum_geometric_mean, reported, places
        )
        dryad_arithmetic_match = _matches_reported_rounding(
            _arithmetic_mean(dryad_values), reported, places
        )
        drum_arithmetic_match = _matches_reported_rounding(
            _arithmetic_mean(drum_values), reported, places
        )
        dryad_rounding_matches += dryad_match
        drum_rounding_matches += drum_match
        dryad_arithmetic_matches += dryad_arithmetic_match
        drum_arithmetic_matches += drum_arithmetic_match
        dryad_near_mismatches += not dryad_match and abs(dryad_residual) <= 1.0
        drum_near_mismatches += not drum_match and abs(drum_residual) <= 1.0
        aggregation_results.append({
            'sample_id': sample_index + 1,
            'species': mucus_data.SPECIES[column % 4],
            'particle_type': 'bEV' if column < 4 else 'whole_bacterium',
            'reported_decimal_places': places,
            'dryad_geometric_mean_matches_reported_rounding': dryad_match,
            'drum_geometric_mean_matches_reported_rounding': drum_match,
            'dryad_geometric_mean_residual_reported_units': dryad_residual,
            'drum_geometric_mean_residual_reported_units': drum_residual,
            'dryad_arithmetic_mean_matches_reported_rounding': dryad_arithmetic_match,
            'drum_arithmetic_mean_matches_reported_rounding': drum_arithmetic_match,
        })
    dryad_count = sum(map(len, dryad_columns))
    drum_count = sum(map(len, drum_columns))
    measurement_hierarchy = {
        'independent_biological_unit': 'human_cervicovaginal_mucus_sample',
        'independent_biological_unit_count': len(drum_summaries),
        'nested_observation': 'individual_particle_one_second_msd',
        'within_sample_factors': ['species', 'particle_type'],
        'sample_species_particle_group_count': len(drum_columns),
        'particle_values_are_independent_biological_replicates': False,
        'summary_statistic_for_fitting': None,
        'constraint': (
            'Any future fit must preserve sample grouping and must not treat nested '
            'particle values as independent biological replicates.'
        ),
    }
    observation_model = {
        'measurement_quantity': 'mean_squared_displacement',
        'lag_time_s': 1.0,
        'measurement_unit': 'micron^2',
        'measurement_space': 'particle_tracking',
        'simulation_space': 'continuum_concentration_field',
        'mapping_status': 'not_validated',
        'simulation_observable': None,
        'parameter_mapping': None,
        'normal_diffusion_established': False,
        'constraint': (
            'A single-lag particle MSD must not be converted to a BioFVM diffusion '
            'coefficient without a validated observation mapping and diffusion-regime evidence.'
        ),
    }
    raw_identical = not (
        representation_only or substantive or unpaired_drum or unpaired_dryad
        or summary_mismatches
    )
    fitting_blockers = []
    if substantive or unpaired_drum or unpaired_dryad:
        fitting_blockers.append({
            'code': 'unresolved_snapshot_difference',
            'detail': (
                'The verified snapshots differ in substantive or unpaired ordered values, '
                'and the upstream cause is not established.'
            ),
            'required_evidence': (
                'A source-controlled processing record or author clarification must explain '
                'every substantive or unpaired value difference between the verified snapshots.'
            ),
        })
    if (
        not comparable_summaries
        or dryad_rounding_matches != len(aggregation_results)
        or drum_rounding_matches != len(aggregation_results)
    ):
        fitting_blockers.append({
            'code': 'unreproduced_summary_aggregation',
            'detail': (
                'The stored summaries are not all reproduced by the documented geometric-mean '
                'rounding check over supplied values.'
            ),
            'required_evidence': (
                'The original analysis code or an author-documented method must specify '
                'preprocessing, exclusions and the summary calculation sufficiently to '
                'reproduce every stored group summary.'
            ),
        })
    if exclusion_provenance['cvm_filtering_status'] == 'unknown':
        fitting_blockers.append({
            'code': 'unknown_cvm_filtering',
            'detail': 'The deposited CVM values have no documented filtering status.',
            'required_evidence': (
                'A source record or author clarification must state whether CVM particle '
                'values were filtered and, if so, specify the inclusion or exclusion rule.'
            ),
        })
    fitting_blockers.append(
        {
            'code': 'no_validated_msd_to_continuum_mapping',
            'detail': (
                'The source reports particle-tracking MSD at one lag while BioFVM predicts '
                'continuum concentration fields; no validated observable or parameter '
                'mapping connects them.'
            ),
            'required_evidence': (
                'Context-matched trajectory or multi-lag evidence plus a validated '
                'observation model must establish the diffusion regime and map the '
                'measured particle MSD to a BioFVM observable or parameter.'
            ),
        }
    )
    parameter_fitting_gate = {
        'ready_for_parameter_fitting': not fitting_blockers,
        'blocker_codes': [blocker['code'] for blocker in fitting_blockers],
        'blockers': fitting_blockers,
    }
    return {
        'schema': 'vesiclescope.mucus-snapshot-reconciliation',
        'version': 1,
        'sources': {
            'dryad': {
                'doi': '10.5061/dryad.cvdncjth8',
                'version_number': 3,
                'license': 'CC0-1.0',
                'container': dryad_container,
            },
            'drum': {
                'doi': '10.13016/kkai-hwng',
                'sha256': drum_digest,
                'size_bytes': drum_size,
                'license': 'CC-BY-NC-ND-3.0-US',
            },
        },
        'reader': {'name': 'openpyxl', 'version': reader_version},
        'cvm_exclusion_provenance': exclusion_provenance,
        'measurement_hierarchy': measurement_hierarchy,
        'observation_model': observation_model,
        'comparison_scope': 'ordered one-second MSD particle values and stored sample summaries',
        'group_count': len(drum_columns),
        'dryad_value_count': dryad_count,
        'drum_value_count': drum_count,
        'exact_shared_value_count': exact,
        'representation_relative_tolerance': REPRESENTATION_REL_TOLERANCE,
        'representation_only_difference_count': representation_only,
        'substantive_value_mismatch_count': substantive,
        'unpaired_drum_value_count': unpaired_drum,
        'unpaired_dryad_value_count': unpaired_dryad,
        'summary_cell_mismatch_count': summary_mismatches,
        'summary_aggregation': {
            'performed': comparable_summaries,
            'group_count': len(aggregation_results),
            'precondition': 'all stored Dryad and DRUM summary cells are numerically equal',
            'method': 'geometric mean of all supplied nonnegative values; zero if any value is zero',
            'rounding_rule': (
                'absolute difference from the stored summary is at most half one unit '
                'at its recorded decimal place'
            ),
            'dryad_rounding_match_count': (
                dryad_rounding_matches if comparable_summaries else None
            ),
            'drum_rounding_match_count': (
                drum_rounding_matches if comparable_summaries else None
            ),
            'snapshot_specific_result_count': (
                sum(
                    result['dryad_geometric_mean_matches_reported_rounding']
                    != result['drum_geometric_mean_matches_reported_rounding']
                    for result in aggregation_results
                )
                if comparable_summaries
                else None
            ),
            'arithmetic_mean_negative_control': {
                'method': 'arithmetic mean of all supplied values',
                'purpose': (
                    "test whether the Dryad README term 'average' can be interpreted "
                    'as the arithmetic mean of every supplied value'
                ),
                'dryad_rounding_match_count': (
                    dryad_arithmetic_matches if comparable_summaries else None
                ),
                'drum_rounding_match_count': (
                    drum_arithmetic_matches if comparable_summaries else None
                ),
            },
            'geometric_mean_residuals': {
                'definition': (
                    '(recomputed geometric mean - stored summary) divided by one unit '
                    'at the stored summary decimal place'
                ),
                'rounding_match_limit_absolute_reported_units': 0.5,
                'near_mismatch_limit_absolute_reported_units': 1.0,
                'near_mismatch_is_accepted': False,
                'dryad_mismatch_within_one_reported_unit_count': (
                    dryad_near_mismatches if comparable_summaries else None
                ),
                'drum_mismatch_within_one_reported_unit_count': (
                    drum_near_mismatches if comparable_summaries else None
                ),
            },
            'group_results': aggregation_results,
        },
        'raw_snapshots_identical': raw_identical,
        'parameter_fitting_gate': parameter_fitting_gate,
        'ready_for_parameter_fitting': parameter_fitting_gate['ready_for_parameter_fitting'],
        'limitations': [
            'Numeric proximity classifies parser representation only; every such difference is reported.',
            'Unpaired ordered values do not establish why values were excluded or omitted upstream.',
            'Particle values within one sample are not independent biological replicates.',
            'No one-second MSD value is converted into a diffusion coefficient or simulation parameter.',
        ],
        'group_differences': group_differences,
    }
