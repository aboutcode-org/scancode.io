# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from scanpipe.pipes.compliance_thresholds import get_project_scorecard_thresholds


def evaluate_scorecard_compliance(project):
    """
    Evaluate scorecard compliance for all discovered packages in the project.

    This function checks OpenSSF Scorecard scores against project-defined
    thresholds and determines the worst compliance alert level across all packages.
    Updates the project's extra_data with the overall compliance status.
    """
    scorecard_policy = get_project_scorecard_thresholds(project)
    if not scorecard_policy:
        return

    worst_alert = None
    packages_with_scores = project.discoveredpackages.filter(
        scores__scoring_tool="ossf-scorecard"
    ).distinct()

    for package in packages_with_scores:
        latest_score = (
            package.scores.filter(scoring_tool="ossf-scorecard")
            .order_by("-score_date")
            .first()
        )

        if not latest_score or latest_score.score is None:
            continue

        try:
            score = float(latest_score.score)
            alert = scorecard_policy.get_alert_for_score(score)
        except Exception:
            alert = "error"

        order = {"ok": 0, "warning": 1, "error": 2}
        if worst_alert is None or order[alert] > order.get(worst_alert, -1):
            worst_alert = alert

    if worst_alert is not None:
        project.update_extra_data({"scorecard_compliance_alert": worst_alert})
