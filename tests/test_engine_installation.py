from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from vesiclescope.engines.biofvm import pinned_engine_metadata
from vesiclescope.engines.installation import (
    _compile_command,
    engine_setup_status,
    verify_physicell_checkout,
)


class EngineInstallationTests(unittest.TestCase):
    def test_status_exposes_reviewed_pin_without_network(self) -> None:
        status = engine_setup_status()
        metadata = pinned_engine_metadata()
        self.assertEqual(status.metadata, metadata)
        self.assertIn(metadata.physicell_commit, str(status.default_physicell_dir))
        self.assertIn(metadata.physicell_commit, str(status.default_runner_path))

    def test_verified_checkout_requires_exact_commit_and_biofvm_version(self) -> None:
        metadata = pinned_engine_metadata()
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / ".git").mkdir()
            biofvm = checkout / "BioFVM"
            biofvm.mkdir()
            (biofvm / "BioFVM_MultiCellDS.cpp").write_text(
                f'const char* BioFVM_Version = "{metadata.biofvm_version}";\n',
                encoding="utf-8",
            )
            completed = subprocess.CompletedProcess(
                args=["git"],
                returncode=0,
                stdout=metadata.physicell_commit + "\n",
                stderr="",
            )
            with patch(
                "vesiclescope.engines.installation._run_checked",
                return_value=completed,
            ):
                self.assertEqual(
                    verify_physicell_checkout(checkout, metadata),
                    metadata,
                )

    def test_verified_checkout_rejects_wrong_commit(self) -> None:
        metadata = pinned_engine_metadata()
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / ".git").mkdir()
            biofvm = checkout / "BioFVM"
            biofvm.mkdir()
            (biofvm / "BioFVM_MultiCellDS.cpp").write_text(
                f'const char* BioFVM_Version = "{metadata.biofvm_version}";\n',
                encoding="utf-8",
            )
            completed = subprocess.CompletedProcess(
                args=["git"],
                returncode=0,
                stdout="0" * 40 + "\n",
                stderr="",
            )
            with patch(
                "vesiclescope.engines.installation._run_checked",
                return_value=completed,
            ):
                with self.assertRaisesRegex(ValueError, "commit"):
                    verify_physicell_checkout(checkout, metadata)

    def test_compile_command_pins_metadata_and_expected_biofvm_sources(self) -> None:
        metadata = pinned_engine_metadata()
        command = _compile_command(
            compiler="/usr/bin/g++",
            runner_source=Path("/package/transport_runner.cpp"),
            physicell_dir=Path("/physicell"),
            output_path=Path("/out/runner"),
            metadata=metadata,
        )
        joined = " ".join(command)
        self.assertIn(str(metadata.physicell_release), joined)
        self.assertIn(metadata.physicell_commit, joined)
        self.assertIn(metadata.biofvm_version, joined)
        self.assertIn("BioFVM_basic_agent.cpp", joined)
        self.assertIn("BioFVM_agent_container.cpp", joined)
        self.assertEqual(command[-2:], ["-o", "/out/runner"])


if __name__ == "__main__":
    unittest.main()
