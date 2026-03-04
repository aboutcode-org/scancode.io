"""
Sample Pipeline: Code Origin Detection

This pipeline demonstrates how to use the Code Origin Determination feature
to detect and store origin information for scanned code files.

This is a reference implementation showing integration patterns.
"""

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scancode
from scanpipe import origin_utils


class DetectCodeOrigins(Pipeline):
    """
    A pipeline that detects code origins from scan results.
    
    This pipeline:
    1. Runs ScanCode to detect packages and licenses
    2. Analyzes package data to determine origins
    3. Creates origin determinations with confidence scores
    4. Handles multiple detection methods (package data, URLs, repositories)
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.collect_codebase_resources,
            cls.run_scancode_scan,
            cls.detect_origins_from_packages,
            cls.detect_origins_from_urls,
            cls.detect_origins_from_repositories,
            cls.calculate_confidence_scores,
        )

    def copy_inputs_to_codebase_directory(self):
        """Copy input files to the codebase directory."""
        self.project.copy_input_to(self.project.codebase_path)

    def collect_codebase_resources(self):
        """Collect all files and directories in the codebase."""
        self.project.create_codebase_resources(self.project.codebase_path)

    def run_scancode_scan(self):
        """Run ScanCode to detect packages, licenses, and copyrights."""
        scancode.run_scancode(
            location=str(self.project.codebase_path),
            output_file=self.project.get_output_file_path("scancode", "json"),
            options=[
                "--copyright",
                "--email",
                "--url",
                "--info",
                "--package",
                "--license",
            ],
        )
        
        # Load the results
        scancode.load_scan_results(
            project=self.project,
            input_location=self.project.get_output_file_path("scancode", "json"),
        )

    def detect_origins_from_packages(self):
        """
        Detect origins from package data in resources.
        Create origin determinations for files with package information.
        """
        resources_with_packages = self.project.codebaseresources.filter(
            package_data__isnull=False
        ).exclude(package_data=[])
        
        for resource in resources_with_packages:
            if hasattr(resource, 'origin_determination'):
                continue  # Skip if already has origin
            
            for package_data in resource.package_data:
                # Try to create origin from package data
                origin = origin_utils.create_origin_from_package_data(
                    resource=resource,
                    package_data=package_data,
                    confidence=0.85,
                    method="scancode-package-detection"
                )
                
                if origin:
                    # Only create one origin per resource (first match)
                    break

    def detect_origins_from_urls(self):
        """
        Detect origins from URLs found in scan results.
        Looks for repository URLs, download URLs, etc.
        """
        resources_with_urls = self.project.codebaseresources.filter(
            urls__isnull=False
        ).exclude(urls=[])
        
        for resource in resources_with_urls:
            if hasattr(resource, 'origin_determination'):
                continue
            
            # Look for repository URLs
            for url_data in resource.urls:
                url = url_data.get('url', '')
                
                # Common repository hosting patterns
                repo_patterns = [
                    'github.com',
                    'gitlab.com',
                    'bitbucket.org',
                    'sourceforge.net',
                ]
                
                if any(pattern in url.lower() for pattern in repo_patterns):
                    origin = origin_utils.create_origin_from_repository(
                        resource=resource,
                        repo_url=url,
                        confidence=0.75,
                        method="url-based-detection"
                    )
                    if origin:
                        break

    def detect_origins_from_repositories(self):
        """
        Detect origins for resources based on discovered packages.
        Links resources to packages and uses package origins.
        """
        packages = self.project.discoveredpackages.all()
        
        for package in packages:
            # Get package URL or repository URL
            origin_identifier = None
            origin_type = None
            confidence = 0.9
            
            if package.package_url:
                origin_identifier = package.package_url
                origin_type = "package"
            elif package.repository_homepage_url:
                origin_identifier = package.repository_homepage_url
                origin_type = "repository"
            elif package.code_view_url:
                origin_identifier = package.code_view_url
                origin_type = "repository"
            
            if not origin_identifier:
                continue
            
            # Find resources related to this package
            related_resources = package.codebase_resources.all()
            
            for resource in related_resources:
                if hasattr(resource, 'origin_determination'):
                    continue
                
                from scanpipe.models import CodeOriginDetermination
                CodeOriginDetermination.objects.create(
                    codebase_resource=resource,
                    detected_origin_type=origin_type,
                    detected_origin_identifier=origin_identifier,
                    detected_origin_confidence=confidence,
                    detected_origin_method="package-association",
                    detected_origin_metadata={
                        "package_uuid": str(package.uuid),
                        "package_name": package.name,
                        "package_version": package.version,
                    }
                )

    def calculate_confidence_scores(self):
        """
        Recalculate confidence scores based on multiple factors.
        This step refines initial confidence scores using heuristics.
        """
        from scanpipe.models import CodeOriginDetermination
        
        origins = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project
        )
        
        for origin in origins:
            resource = origin.codebase_resource
            base_confidence = origin.detected_origin_confidence
            
            # Adjust confidence based on various factors
            adjustments = []
            
            # Factor 1: License information increases confidence
            if resource.detected_license_expression:
                adjustments.append(0.05)
            
            # Factor 2: Copyright information increases confidence
            if resource.copyrights:
                adjustments.append(0.05)
            
            # Factor 3: Package association increases confidence
            if resource.discovered_packages.exists():
                adjustments.append(0.1)
            
            # Factor 4: PURL format increases confidence
            if origin.detected_origin_identifier.startswith('pkg:'):
                adjustments.append(0.05)
            
            # Calculate final confidence (capped at 1.0)
            final_confidence = min(1.0, base_confidence + sum(adjustments))
            
            if final_confidence != base_confidence:
                origin_utils.update_origin_confidence(
                    origin_uuid=origin.uuid,
                    new_confidence=final_confidence,
                    reason="confidence-adjustment-heuristics"
                )


# Usage example in a custom pipeline:
"""
from scanpipe.pipelines import Pipeline
from scanpipe import origin_utils

class MyCustomPipeline(Pipeline):
    
    @classmethod
    def steps(cls):
        return (
            # ... your other steps ...
            cls.detect_code_origins,
            cls.generate_origin_report,
        )
    
    def detect_code_origins(self):
        # Custom logic to detect origins
        scan_results = []
        
        for resource in self.project.codebaseresources.files():
            # Your detection logic here
            origin_info = {
                'path': resource.path,
                'origin_type': 'package',
                'origin_identifier': 'pkg:npm/example@1.0.0',
                'confidence': 0.8,
                'method': 'custom-detector',
                'metadata': {'custom_field': 'value'}
            }
            scan_results.append(origin_info)
        
        # Bulk create origins
        created, skipped = origin_utils.bulk_create_origins_from_scan_results(
            project=self.project,
            scan_results=scan_results
        )
        
        self.log(f"Created {created} origin determinations, skipped {skipped}")
    
    def generate_origin_report(self):
        # Generate statistics
        stats = origin_utils.get_origin_statistics(self.project)
        
        self.log(f"Origin Statistics:")
        self.log(f"  Total: {stats['total']}")
        self.log(f"  Verified: {stats['verified']} ({stats['verified_percentage']:.1f}%)")
        self.log(f"  Amended: {stats['amended']} ({stats['amended_percentage']:.1f}%)")
        self.log(f"  Average Confidence: {stats['average_confidence']:.2f}")
        self.log(f"  High Confidence: {stats['high_confidence_count']}")
        self.log(f"  Medium Confidence: {stats['medium_confidence_count']}")
        self.log(f"  Low Confidence: {stats['low_confidence_count']}")
"""
