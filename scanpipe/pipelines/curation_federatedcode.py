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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode
from scanpipe import curation_utils


class ExportCurationsToFederatedCode(Pipeline):
    """
    Export origin curations to a FederatedCode Git repository.
    
    This pipeline exports verified origin determinations from a project
    as shareable curation packages that can be imported by other ScanCode.io
    instances or used by the broader open-source community.
    
    The exported curations include:
    - Origin type and identifier (package, repository, URL, etc.)
    - Confidence scores and detection methods
    - Verification status and manual amendments
    - Full provenance chain (who, when, from where)
    - Propagation information (if applicable)
    
    Curations are committed to a Git repository following the FederatedCode
    structure, organized by package PURL.
    """
    
    @classmethod
    def steps(cls):
        return (
            cls.check_project_eligibility,
            cls.export_curations_to_federatedcode,
        )
    
    def check_project_eligibility(self):
        """Check if project is eligible for curation export."""
        self.log("Checking project eligibility for curation export")
        
        # Check FederatedCode configuration
        if not federatedcode.is_configured():
            self.log("FederatedCode is not configured", level=self.ERROR)
            raise Exception(
                "FederatedCode is not configured. "
                "Please set FEDERATEDCODE_GIT_ACCOUNT_URL and related settings."
            )
        
        # Check if we're available
        if not federatedcode.is_available():
            self.log("FederatedCode Git service is not available", level=self.WARNING)
        
        # Check basic project requirements
        errors = federatedcode.check_federatedcode_eligibility(self.project)
        if errors:
            self.log(f"Project eligibility errors: {'; '.join(errors)}", level=self.ERROR)
            raise Exception(f"Project not eligible for export: {'; '.join(errors)}")
        
        # Check if there are curations to export
        from scanpipe.models import CodeOriginDetermination
        
        verified_count = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project,
            is_verified=True,
        ).count()
        
        if verified_count == 0:
            self.log("No verified curations to export", level=self.WARNING)
            raise Exception("No verified origin determinations found to export")
        
        self.log(f"Found {verified_count} verified curations to export")
    
    def export_curations_to_federatedcode(self):
        """Export curations to FederatedCode repository."""
        self.log("Exporting curations to FederatedCode")
        
        # Get curator information from project execution
        curator_name = self.env.get("curator_name", "")
        curator_email = self.env.get("curator_email", "")
        verified_only = self.env.get("verified_only", True)
        include_propagated = self.env.get("include_propagated", False)
        
        # Export
        success, message = curation_utils.export_curations_to_federatedcode(
            project=self.project,
            curator_name=curator_name,
            curator_email=curator_email,
            verified_only=verified_only,
            include_propagated=include_propagated,
        )
        
        if success:
            self.log(message, level=self.INFO)
        else:
            self.log(message, level=self.ERROR)
            raise Exception(f"Export failed: {message}")


class ImportCurationsFromFederatedCode(Pipeline):
    """
    Import origin curations from an external FederatedCode source.
    
    This pipeline imports curations from external sources such as:
    - Other ScanCode.io instances
    - Community FederatedCode repositories
    - Manually curated curation packages
    
    The import process:
    1. Fetches curations from the specified source (Git repo or URL)
    2. Validates the curation package schema
    3. Matches file curations to codebase resources
    4. Detects conflicts with existing curations
    5. Applies the specified conflict resolution strategy
    6. Creates/updates origin determinations
    7. Records full provenance
    
    Conflict resolution strategies:
    - manual_review: Create conflict records for manual resolution (default)
    - keep_existing: Keep existing curations, skip imports
    - use_imported: Replace existing with imported curations
    - highest_confidence: Use curation with higher confidence score
    - highest_priority: Use source with higher priority
    """
    
    @classmethod
    def steps(cls):
        return (
            cls.validate_import_parameters,
            cls.import_curations,
            cls.report_import_results,
        )
    
    def validate_import_parameters(self):
        """Validate required parameters for import."""
        self.log("Validating import parameters")
        
        # Get source URL from environment
        self.source_url = self.env.get("source_url")
        if not self.source_url:
            raise Exception(
                "Missing required parameter: source_url. "
                "Provide URL to FederatedCode Git repository or curation file."
            )
        
        self.log(f"Import source: {self.source_url}")
        
        # Get optional parameters
        self.source_name = self.env.get("source_name", "")
        self.conflict_strategy = self.env.get("conflict_strategy", "manual_review")
        self.dry_run = self.env.get("dry_run", False)
        
        valid_strategies = [
            "manual_review",
            "keep_existing",
            "use_imported",
            "highest_confidence",
            "highest_priority",
        ]
        
        if self.conflict_strategy not in valid_strategies:
            raise Exception(
                f"Invalid conflict_strategy: {self.conflict_strategy}. "
                f"Valid options: {', '.join(valid_strategies)}"
            )
        
        self.log(f"Conflict strategy: {self.conflict_strategy}")
        if self.dry_run:
            self.log("DRY RUN MODE - No changes will be made", level=self.WARNING)
    
    def import_curations(self):
        """Import curations from external source."""
        self.log("Importing curations")
        
        success, stats = curation_utils.import_curations_from_url(
            project=self.project,
            source_url=self.source_url,
            source_name=self.source_name,
            conflict_strategy=self.conflict_strategy,
            dry_run=self.dry_run,
        )
        
        self.import_stats = stats
        
        if not success:
            error = stats.get("error", "Unknown error")
            self.log(f"Import failed: {error}", level=self.ERROR)
            raise Exception(f"Import failed: {error}")
    
    def report_import_results(self):
        """Report import statistics."""
        self.log("Import Results:")
        self.log(f"  Total curations: {self.import_stats.get('total', 0)}")
        self.log(f"  Imported: {self.import_stats.get('imported', 0)}")
        self.log(f"  Updated: {self.import_stats.get('updated', 0)}")
        self.log(f"  Skipped: {self.import_stats.get('skipped', 0)}")
        self.log(f"  Conflicts: {self.import_stats.get('conflicts', 0)}")
        self.log(f"  Errors: {self.import_stats.get('errors', 0)}")
        
        if self.import_stats.get('error_details'):
            self.log("Error details:", level=self.WARNING)
            for error in self.import_stats['error_details'][:10]:  # Limit to first 10
                self.log(f"  - {error}", level=self.WARNING)
        
        if self.import_stats.get('conflicts', 0) > 0:
            self.log(
                f"{self.import_stats['conflicts']} conflicts created. "
                "Review them in the admin interface or use the "
                "resolve-curation-conflicts management command.",
                level=self.WARNING,
            )


class ExportCurationsToFile(Pipeline):
    """
    Export origin curations to a local file.
    
    This pipeline exports curations to a local JSON or YAML file for:
    - Manual distribution
    - Archival purposes
    - Integration with external systems
    - Testing and development
    
    Unlike ExportCurationsToFederatedCode, this pipeline exports to a local
    file and does not interact with Git repositories.
    """
    
    @classmethod
    def steps(cls):
        return (
            cls.validate_export_parameters,
            cls.export_curations_to_file,
        )
    
    def validate_export_parameters(self):
        """Validate export parameters."""
        self.log("Validating export parameters")
        
        # Get output path
        self.output_path = self.env.get("output_path")
        if not self.output_path:
            # Default to project work directory
            from pathlib import Path
            self.output_path = (
                self.project.project_work_directory / "curations" / "origins.json"
            )
        
        self.log(f"Output path: {self.output_path}")
        
        # Get format
        self.format = self.env.get("format", "json")
        if self.format not in ["json", "yaml"]:
            raise Exception(f"Invalid format: {self.format}. Must be 'json' or 'yaml'")
        
        # Get export options
        self.verified_only = self.env.get("verified_only", True)
        self.include_propagated = self.env.get("include_propagated", False)
        self.include_provenance = self.env.get("include_provenance", True)
        self.curator_name = self.env.get("curator_name", "")
        self.curator_email = self.env.get("curator_email", "")
    
    def export_curations_to_file(self):
        """Export curations to file."""
        self.log(f"Exporting curations to {self.format.upper()} file")
        
        from pathlib import Path
        
        success, result = curation_utils.export_curations_to_file(
            project=self.project,
            output_path=Path(self.output_path),
            format=self.format,
            verified_only=self.verified_only,
            include_propagated=self.include_propagated,
            include_provenance=self.include_provenance,
            curator_name=self.curator_name,
            curator_email=self.curator_email,
        )
        
        if success:
            self.log(f"Successfully exported curations to: {result}")
        else:
            self.log(f"Export failed: {result}", level=self.ERROR)
            raise Exception(f"Export failed: {result}")
