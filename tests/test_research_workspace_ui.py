import unittest
from importlib.resources import files


class ResearchWorkspaceUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = files("vesiclescope.ui").joinpath("static/index.html").read_text(
            encoding="utf-8"
        )

    def test_exposes_measurement_and_phenotype_research_views(self) -> None:
        for expected in (
            'id="researchWorkspace"',
            'id="measurementImport"',
            'id="perturbationImport"',
            'id="measurementView"',
            'id="phenotypeCards"',
            "total_or_unmarked",
            "marker_defined",
            "cargo",
            "Explicitly unknown",
            "Limitations",
        ):
            self.assertIn(expected, self.html)

    def test_population_comparison_uses_independent_discrete_snapshots(self) -> None:
        for expected in (
            'id="populationRunSelect"',
            'id="leftPopulation"',
            'id="rightPopulation"',
            'id="leftTime"',
            'id="rightTime"',
            'id="leftStoredTime"',
            'id="rightStoredTime"',
            'id="populationLeftCanvas"',
            'id="populationRightCanvas"',
            "Shared scale",
            "stored snapshots only",
            "No interpolation",
        ):
            self.assertIn(expected, self.html)
        self.assertIn("function selectedSnapshot", self.html)
        self.assertIn("A shared scale would be scientifically invalid", self.html)
        self.assertNotIn("interpolateSnapshot", self.html)

    def test_population_study_execution_requires_explicit_server_mapping(self) -> None:
        for expected in (
            'id="populationExecution"',
            'id="populationExperimentMappings"',
            'id="populationRunName"',
            'id="populationGridSpacing"',
            'id="populationTimeStep"',
            'id="executePopulationStudy"',
            "function renderPopulationExecution",
            "function executePopulationStudy",
            "/api/population-run",
            "Annotation only / do not simulate",
            "population_experiments",
        ):
            self.assertIn(expected, self.html)
        self.assertNotIn("applyPopulationEffect", self.html)

    def test_research_workspace_is_keyboard_and_mobile_ready(self) -> None:
        self.assertIn(":focus-visible", self.html)
        self.assertIn('role="tablist"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn("@media(max-width:720px)", self.html)

    def test_two_run_comparison_exposes_honest_temporal_controls(self) -> None:
        for expected in (
            'id="compareLeftMap"',
            'id="compareRightMap"',
            'id="compareLeftTime"',
            'id="compareRightTime"',
            'id="compareLeftPlay"',
            'id="compareRightPlay"',
            'id="compareSync"',
            'id="comparisonExtracellularCanvas"',
            'id="comparisonInternalizedCanvas"',
            'id="comparisonChangedParameters"',
            'id="comparisonFigureExport"',
            "function synchronizeComparisonTime",
            "function toggleComparisonPlayback",
            "function quantityDifferenceLabel",
            "undefined (left is zero)",
            "latest stored time not after",
            "End-field-only run",
            "/download/comparison-figure",
            "function exportComparisonFigure",
        ):
            self.assertIn(expected, self.html)


if __name__ == "__main__":
    unittest.main()
