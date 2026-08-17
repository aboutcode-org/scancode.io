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

"""Collect and score npm package health information."""

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import npm_health


class NpmHealth(Pipeline):
    """Collect reusable npm package health metrics for one project PURL."""

    download_inputs = False
    is_addon = True
    results_url = "/project/{slug}/"


    def validate_project_purl(self):
        """Validate and parse the project's versioned npm PURL."""
        self.package = npm_health.validate_npm_package_url(self.project.purl)


    def load_cached_snapshot(self):
        """Reuse a fresh project snapshot when one is already available."""
        self.cached_snapshot = None
        snapshot = npm_health.get_cached_snapshot(self.project)
        max_age = int(
            self.env.get(
                "npm_health_cache_max_age_days",
                npm_health.DEFAULT_CACHE_MAX_AGE_DAYS,
            )
        )
        if snapshot and not npm_health.is_stale(snapshot, max_age_days=max_age):
            self.cached_snapshot = snapshot
            self.snapshot = snapshot
            self.log("Using fresh cached npm-health analysis.")


    def fetch_package_metadata(self):
        """Fetch exact npm registry metadata unless a fresh cache is used."""
        if self.cached_snapshot:
            return
        self.metadata = npm_health.fetch_registry_metadata(self.package)


    def collect_package_metrics(self):
        """Collect built-in registry signals and optional external metrics."""
        if self.cached_snapshot:
            return

        baseline = npm_health.collect_registry_metrics(self.metadata)
        external = {}
        command_template = self.env.get("npm_health_metrics_command")
        if command_template:
            output = self.project.tmp_path / "npm-health-external-metrics.json"
            external = npm_health.collect_external_metrics(
                command_template=command_template,
                purl=self.project.purl,
                metadata=self.metadata,
                output=output,
                cwd=self.project.tmp_path,
            )
        self.metrics = npm_health.merge_metrics(baseline, external)
