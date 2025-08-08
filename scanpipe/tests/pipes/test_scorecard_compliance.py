from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from scanpipe.models import DiscoveredPackage
from scanpipe.models import DiscoveredPackageScore
from scanpipe.models import Project
from scanpipe.pipes.compliance_thresholds import ScorecardThresholdsPolicy
from scanpipe.pipes.scorecard_compliance import evaluate_scorecard_compliance


class EvaluateScorecardComplianceTest(TestCase):
    """Test evaluate_scorecard_compliance pipe function."""

    def setUp(self):
        self.project = Project.objects.create(name="test_project")

    def create_package_with_score(self, package_name, score_value):
        """Create a package with a scorecard score."""
        package = DiscoveredPackage.objects.create(
            project=self.project,
            name=package_name,
            type="pypi",
            vcs_url="https://github.com/numpy/numpy",
        )

        DiscoveredPackageScore.objects.create(
            discovered_package=package,
            scoring_tool="ossf-scorecard",
            score=str(score_value),
            scoring_tool_version="v4.10.2",
            score_date=timezone.now(),
        )

        return package

    def test_no_scorecard_policy_configured(self):
        """Test that function returns early when no scorecard policy is configured."""
        with patch(
            "scanpipe.pipes.scorecard_compliance.get_project_scorecard_thresholds"
        ) as mock_get_policy:
            mock_get_policy.return_value = None

            evaluate_scorecard_compliance(self.project)

            self.project.refresh_from_db()
            self.assertNotIn("scorecard_compliance_alert", self.project.extra_data)

    def test_sets_compliance_alert_correctly(self):
        """Test that compliance alert is set correctly based on scores."""
        thresholds = {9.0: "ok", 7.0: "warning", 0: "error"}
        policy = ScorecardThresholdsPolicy(thresholds)

        self.create_package_with_score("good_package", 9.5)

        with patch(
            "scanpipe.pipes.scorecard_compliance.get_project_scorecard_thresholds"
        ) as mock_get_policy:
            mock_get_policy.return_value = policy

            evaluate_scorecard_compliance(self.project)

            self.project.refresh_from_db()
            self.assertEqual(
                self.project.extra_data["scorecard_compliance_alert"], "ok"
            )

    def test_worst_alert_selected_for_multiple_packages(self):
        """Test that worst alert level is selected across multiple packages."""
        thresholds = {9.0: "ok", 7.0: "warning", 0: "error"}
        policy = ScorecardThresholdsPolicy(thresholds)

        self.create_package_with_score("good_package", 9.5)
        self.create_package_with_score("bad_package", 5.0)

        with patch(
            "scanpipe.pipes.scorecard_compliance.get_project_scorecard_thresholds"
        ) as mock_get_policy:
            mock_get_policy.return_value = policy

            evaluate_scorecard_compliance(self.project)

            self.project.refresh_from_db()
            self.assertEqual(
                self.project.extra_data["scorecard_compliance_alert"], "error"
            )

    def test_no_packages_with_scores(self):
        """Test behavior when no packages have scorecard scores."""
        thresholds = {9.0: "ok", 7.0: "warning", 0: "error"}
        policy = ScorecardThresholdsPolicy(thresholds)

        with patch(
            "scanpipe.pipes.scorecard_compliance.get_project_scorecard_thresholds"
        ) as mock_get_policy:
            mock_get_policy.return_value = policy

            evaluate_scorecard_compliance(self.project)

            self.project.refresh_from_db()
            self.assertNotIn("scorecard_compliance_alert", self.project.extra_data)
