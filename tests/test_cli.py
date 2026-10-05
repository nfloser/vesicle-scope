from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from vesiclescope import __version__
from vesiclescope.cli import main


class CliTests(unittest.TestCase):
    def test_default_command_prints_help(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main([])
        self.assertEqual(status, 0)
        self.assertIn("usage: vesiclescope", output.getvalue())
        self.assertIn("examples", output.getvalue())
        self.assertIn("run", output.getvalue())

    def test_examples_are_discoverable_without_running_simulation(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main(["examples"])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("diffusion-uptake-factor", text)
        self.assertIn("synthetic benchmark", text)
        self.assertIn("not experimental evidence", text)

    def test_version_matches_package_version(self) -> None:
        parser_output = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(parser_output):
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(__version__, parser_output.getvalue())

    def test_run_reports_missing_native_runner_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            error = StringIO()
            with redirect_stderr(error):
                status = main(
                    [
                        "run",
                        "diffusion-uptake-factor",
                        "--runner",
                        str(Path(directory) / "missing-runner"),
                        "--revision",
                        "a" * 40,
                        "--output-dir",
                        str(Path(directory) / "output"),
                    ]
                )
        self.assertEqual(status, 2)
        self.assertIn("native runner does not exist", error.getvalue())


if __name__ == "__main__":
    unittest.main()
