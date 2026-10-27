"""Dryad source verification uses generated files, never published measurements."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vesiclescope.cli import main
from vesiclescope.validation import dryad_data


class DryadSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.files = {
            'measurements.csv': b'sample,value\n1,2\n',
            'README.md': b'# Synthetic fixture\n',
        }
        for name, content in self.files.items():
            (self.path / name).write_bytes(content)
        self.expected = tuple(
            {
                'name': name,
                'size_bytes': len(content),
                'sha256': hashlib.sha256(content).hexdigest(),
            }
            for name, content in self.files.items()
        )

    def verify(self):
        with patch.object(dryad_data, 'DRYAD_V3_FILES', self.expected):
            return dryad_data.verify_dryad_v3_directory(self.path)

    def test_exact_snapshot_is_verified_without_modification(self):
        before = {name: (self.path / name).read_bytes() for name in self.files}
        report = self.verify()

        self.assertEqual(
            {name: (self.path / name).read_bytes() for name in self.files},
            before,
        )
        self.assertEqual(report['schema'], 'vesiclescope.dryad-source-verification')
        self.assertEqual(report['source']['doi'], '10.5061/dryad.cvdncjth8')
        self.assertEqual(report['source']['version_number'], 3)
        self.assertEqual(report['verified_file_count'], 2)
        self.assertFalse(report['ready_for_parameter_fitting'])
        self.assertEqual(
            [item['name'] for item in report['files']],
            ['measurements.csv', 'README.md'],
        )

    def test_inventory_must_be_exact(self):
        (self.path / 'measurements.csv').unlink()
        (self.path / 'unexpected.csv').write_text('not expected', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'missing.*measurements.csv.*unexpected.*unexpected.csv'):
            self.verify()

    def test_size_and_digest_must_match_repository_metadata(self):
        (self.path / 'measurements.csv').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'measurements.csv: size'):
            self.verify()

        changed = b'x' * len(self.files['measurements.csv'])
        (self.path / 'measurements.csv').write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'measurements.csv: SHA-256'):
            self.verify()

    def test_non_directory_and_non_regular_entries_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'must be a directory'):
            dryad_data.verify_dryad_v3_directory(self.path / 'missing')

        (self.path / 'README.md').unlink()
        (self.path / 'README.md').mkdir()
        with self.assertRaisesRegex(ValueError, 'regular files'):
            self.verify()

    def test_cli_is_deterministic_and_handles_verification_error(self):
        outputs = []
        with patch.object(dryad_data, 'DRYAD_V3_FILES', self.expected):
            for _ in range(2):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(['data', 'verify-dryad-v3', str(self.path)]), 0)
                outputs.append(output.getvalue())
            (self.path / 'README.md').write_bytes(b'changed')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['data', 'verify-dryad-v3', str(self.path)]), 2)

        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(
            json.loads(outputs[0])['schema'],
            'vesiclescope.dryad-source-verification',
        )


if __name__ == '__main__':
    unittest.main()
