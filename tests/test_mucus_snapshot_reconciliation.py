"""Cross-snapshot tests use generated data, never published measurements."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from vesiclescope.cli import main
from vesiclescope.validation import dryad_data, mucus_data
from vesiclescope.validation.mucus_reconciliation import reconcile_mucus_snapshots


@unittest.skipUnless(importlib.util.find_spec('openpyxl'), 'optional data reader missing')
class MucusSnapshotReconciliationTests(unittest.TestCase):
    def setUp(self):
        from openpyxl import Workbook

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workbook_path = self.root / 'figure2.xlsx'
        self.dryad_path = self.root / 'dryad.zip'

        book = Workbook()
        summary = book.active
        summary.title = '1s MSD GeoMean'
        summary.append(list(mucus_data.SUMMARY_HEADERS))
        for sample in range(1, 11):
            summary.append([4.0] * 8 + [sample, 4.2 if sample <= 5 else 4.3])
            sheet = book.create_sheet(f'Sample {sample}')
            sheet.append(list(mucus_data.PARTICLE_HEADERS))
            sheet.append([1.0] * 8)
            sheet.append([16.0] * 8)
        # The stored Sample 1 / LC bEV summary matches the shorter Dryad
        # sequence (GM 1) but not the two-value DRUM sequence (GM 4).
        summary['A2'] = 1
        # A one-last-place-unit residual exercises magnitude reporting without
        # changing the existing half-unit rounding acceptance rule.
        summary['A3'] = 3
        # Exercise transparent parser-representation classification.
        book['Sample 7']['D2'] = 0.00035705999999999997
        book.save(self.workbook_path)

        raw = io.StringIO(newline='')
        writer = csv.writer(raw, lineterminator='\n')
        writer.writerow([f'Sample {sample}' for sample in range(1, 11) for _ in range(8)])
        writer.writerow(['LC', 'LI', 'GV', 'MM', 'LC', 'LI', 'GV', 'MM'] * 10)
        writer.writerow(['EV'] * 4 + ['WB'] * 4)
        # Repeat particle headers for all samples.
        first = raw.getvalue().splitlines()
        first[2] = ','.join((['EV'] * 4 + ['WB'] * 4) * 10)
        rows = [first[0], first[1], first[2]]
        row_one = ['1'] * 80
        row_one[51] = '0.00035705999999999997'
        rows.append(','.join(row_one))
        # Deliberately omit only the second Sample 1 / LC EV value.
        row_two = [''] + ['16'] * 79
        rows.append(','.join(row_two))
        measurements = ('\n'.join(rows) + '\n').encode()

        sample_info = io.StringIO(newline='')
        info = csv.writer(sample_info, lineterminator='\n')
        info.writerow(['Sample Number', 'LC bEVs', 'LI bEVs', 'GV bEVs', 'MM bEVs',
                       'LC WB', 'LI WB', 'GV WB', 'MM WB', 'pH'])
        for sample in range(1, 11):
            stored = [4] * 8
            if sample == 1:
                stored[0] = 1
            elif sample == 2:
                stored[0] = 3
            info.writerow([sample] + stored + [4.2 if sample <= 5 else 4.3])

        self.files = {
            'bEV_diffusion_host_response_CVM_1sMSD.csv': measurements,
            'bEV_diffusion_host_response_CVM_SampleInfo.csv': sample_info.getvalue().encode(),
            'bEV_diffusion_host_response_bEV_Histogram_removed_outliers.csv': b'GRUBB\n',
            'README.md': (
                b'Removed outliers can be found in the following associated CSV files:\n'
                b'* **bEV_diffusion_host_response_bEV_Histogram_removed_outliers.csv**\n'
            ),
        }
        with zipfile.ZipFile(self.dryad_path, 'w') as archive:
            for name, content in self.files.items():
                archive.writestr(name, content)
        self.expected = tuple({
            'name': name,
            'size_bytes': len(content),
            'sha256': hashlib.sha256(content).hexdigest(),
        } for name, content in self.files.items())
        self.workbook_sha256 = hashlib.sha256(self.workbook_path.read_bytes()).hexdigest()

    def reconcile(self):
        with (
            patch.object(dryad_data, 'DRYAD_V3_FILES', self.expected),
            patch.object(mucus_data, 'REVIEWED_SHA256', self.workbook_sha256),
        ):
            return reconcile_mucus_snapshots(self.workbook_path, self.dryad_path)

    def test_reports_unpaired_value_and_representation_difference_without_fitting(self):
        report = self.reconcile()

        self.assertEqual(report['schema'], 'vesiclescope.mucus-snapshot-reconciliation')
        self.assertEqual(report['drum_value_count'], 160)
        self.assertEqual(report['dryad_value_count'], 159)
        self.assertEqual(report['unpaired_drum_value_count'], 1)
        self.assertEqual(report['unpaired_dryad_value_count'], 0)
        self.assertEqual(report['representation_only_difference_count'], 1)
        self.assertEqual(report['substantive_value_mismatch_count'], 0)
        self.assertEqual(report['summary_cell_mismatch_count'], 0)
        self.assertFalse(report['raw_snapshots_identical'])
        self.assertFalse(report['ready_for_parameter_fitting'])
        exclusion = report['cvm_exclusion_provenance']
        self.assertFalse(exclusion['cvm_removed_outlier_file_present'])
        self.assertEqual(exclusion['cvm_filtering_status'], 'unknown')
        self.assertTrue(exclusion['readme_lists_all_removed_outlier_files'])
        self.assertEqual(exclusion['removed_outlier_file_count'], 1)
        aggregation = report['summary_aggregation']
        self.assertTrue(aggregation['performed'])
        self.assertEqual(aggregation['group_count'], 80)
        difference = next(
            group for group in aggregation['group_results']
            if group['sample_id'] == 1
            and group['species'] == 'L. crispatus'
            and group['particle_type'] == 'bEV'
        )
        self.assertTrue(difference['dryad_geometric_mean_matches_reported_rounding'])
        self.assertFalse(difference['drum_geometric_mean_matches_reported_rounding'])
        self.assertEqual(difference['dryad_geometric_mean_residual_reported_units'], 0.0)
        self.assertEqual(difference['drum_geometric_mean_residual_reported_units'], 3.0)
        self.assertTrue(difference['dryad_arithmetic_mean_matches_reported_rounding'])
        self.assertFalse(difference['drum_arithmetic_mean_matches_reported_rounding'])
        self.assertEqual(difference['reported_decimal_places'], 0)
        arithmetic = aggregation['arithmetic_mean_negative_control']
        self.assertEqual(arithmetic['dryad_rounding_match_count'], 1)
        self.assertEqual(arithmetic['drum_rounding_match_count'], 0)
        residuals = aggregation['geometric_mean_residuals']
        self.assertEqual(residuals['dryad_mismatch_within_one_reported_unit_count'], 1)
        self.assertEqual(residuals['drum_mismatch_within_one_reported_unit_count'], 1)
        near = next(
            group for group in aggregation['group_results']
            if group['sample_id'] == 2
            and group['species'] == 'L. crispatus'
            and group['particle_type'] == 'bEV'
        )
        self.assertEqual(near['dryad_geometric_mean_residual_reported_units'], 1.0)
        mismatch = report['group_differences'][0]
        self.assertEqual((mismatch['sample_id'], mismatch['species'], mismatch['particle_type']),
                         (1, 'L. crispatus', 'bEV'))
        self.assertEqual(mismatch['unpaired_drum_value_count'], 1)
        self.assertEqual(mismatch['ordered_sequence_relation'], 'dryad_is_exact_prefix_of_drum')
        self.assertEqual(mismatch['first_unpaired_ordinal'], 2)
        representation_group = next(
            group for group in report['group_differences']
            if group['representation_only_difference_count']
        )
        self.assertEqual(
            representation_group['ordered_sequence_relation'],
            'representation_equivalent_equal',
        )
        self.assertIsNone(representation_group['first_unpaired_ordinal'])

    def test_substantive_value_and_summary_mismatches_are_not_hidden(self):
        with zipfile.ZipFile(self.dryad_path, 'r') as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        files['bEV_diffusion_host_response_CVM_1sMSD.csv'] = files[
            'bEV_diffusion_host_response_CVM_1sMSD.csv'
        ].replace(b',1,1,1,', b',2,1,1,', 1)
        files['bEV_diffusion_host_response_CVM_SampleInfo.csv'] = files[
            'bEV_diffusion_host_response_CVM_SampleInfo.csv'
        ].replace(b',4,4,4,', b',5,4,4,', 1)
        with zipfile.ZipFile(self.dryad_path, 'w') as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        self.files = files
        self.expected = tuple({
            'name': name,
            'size_bytes': len(content),
            'sha256': hashlib.sha256(content).hexdigest(),
        } for name, content in files.items())

        report = self.reconcile()

        self.assertEqual(report['substantive_value_mismatch_count'], 1)
        self.assertEqual(report['summary_cell_mismatch_count'], 1)
        self.assertFalse(report['summary_aggregation']['performed'])
        self.assertIsNone(report['summary_aggregation']['dryad_rounding_match_count'])
        self.assertIsNone(
            report['summary_aggregation']['arithmetic_mean_negative_control'][
                'dryad_rounding_match_count'
            ]
        )
        self.assertIsNone(
            report['summary_aggregation']['geometric_mean_residuals'][
                'dryad_mismatch_within_one_reported_unit_count'
            ]
        )
        self.assertEqual(report['summary_aggregation']['group_results'], [])
        substantive_group = next(
            group for group in report['group_differences']
            if group['substantive_value_mismatch_count']
        )
        self.assertEqual(substantive_group['ordered_sequence_relation'], 'not_equal_or_prefix')

    def test_cli_is_deterministic(self):
        outputs = []
        with (
            patch.object(dryad_data, 'DRYAD_V3_FILES', self.expected),
            patch.object(mucus_data, 'REVIEWED_SHA256', self.workbook_sha256),
        ):
            for _ in range(2):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main([
                        'data', 'reconcile-mucus-snapshots',
                        str(self.workbook_path), str(self.dryad_path),
                    ]), 0)
                outputs.append(output.getvalue())

        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(
            json.loads(outputs[0])['schema'],
            'vesiclescope.mucus-snapshot-reconciliation',
        )

    def test_committed_manifest_preserves_actual_reconciliation_gate(self):
        manifest = json.loads((
            Path(__file__).parents[1]
            / 'docs' / 'research' / 'public-ev-data-manifest.json'
        ).read_text(encoding='utf-8'))
        reconciliation = manifest['reconciliation']

        self.assertEqual(reconciliation['dryad_value_count'], 19281)
        self.assertEqual(reconciliation['drum_value_count'], 19430)
        self.assertEqual(reconciliation['unpaired_drum_value_count'], 149)
        self.assertEqual(reconciliation['substantive_value_mismatch_count'], 0)
        self.assertEqual(reconciliation['position_verified_on'], '2026-11-01')
        self.assertEqual(reconciliation['aggregation_verified_on'], '2026-11-02')
        self.assertEqual(reconciliation['dryad_summary_rounding_match_count'], 59)
        self.assertEqual(reconciliation['drum_summary_rounding_match_count'], 58)
        self.assertEqual(reconciliation['snapshot_specific_summary_result_count'], 1)
        self.assertEqual(reconciliation['dryad_arithmetic_mean_rounding_match_count'], 0)
        self.assertEqual(reconciliation['drum_arithmetic_mean_rounding_match_count'], 0)
        self.assertEqual(reconciliation['aggregation_language_verified_on'], '2026-11-03')
        self.assertEqual(reconciliation['residual_magnitude_verified_on'], '2026-11-04')
        self.assertEqual(reconciliation['dryad_mismatch_within_one_reported_unit_count'], 10)
        self.assertEqual(reconciliation['drum_mismatch_within_one_reported_unit_count'], 10)
        self.assertEqual(reconciliation['exclusion_provenance_verified_on'], '2026-11-05')
        self.assertFalse(reconciliation['cvm_removed_outlier_file_present'])
        self.assertEqual(reconciliation['cvm_filtering_status'], 'unknown')
        self.assertEqual(reconciliation['other_assay_removed_outlier_file_count'], 5)
        self.assertEqual(
            reconciliation['different_group']['ordered_sequence_relation'],
            'dryad_is_exact_prefix_of_drum',
        )
        self.assertEqual(reconciliation['different_group']['first_unpaired_ordinal'], 86)
        self.assertFalse(reconciliation['ready_for_parameter_fitting'])


if __name__ == '__main__':
    unittest.main()
