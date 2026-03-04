"""
Pipeline: Code Origin Detection with Propagation

This pipeline detects code origins from scan results and then propagates
confirmed origins to similar/related files using multiple signals:
- Package membership
- Path patterns and directory structure
- License similarity

This demonstrates the complete origin determination workflow including
both automated detection and intelligent propagation.
"""

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import scancode
from scanpipe import origin_utils


class DetectAndPropagateOrigins(Pipeline):
    """
    A pipeline that detects code origins and propagates them to related files.
    
    This pipeline:
    1. Runs ScanCode to detect packages and licenses
    2. Detects origins from package data and other signals
    3. Propagates high-confidence origins to similar/related files
    4. Generates propagation statistics
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
            cls.mark_high_confidence_as_verified,
            cls.propagate_origins_by_package,
            cls.propagate_origins_by_path,
            cls.propagate_origins_by_license,
            cls.generate_propagation_report,
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
        
        created_count = 0
        
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
                    created_count += 1
                    # Only create one origin per resource (first match)
                    break
        
        self.project.add_info(
            f"Created {created_count} origin determinations from package data"
        )

    def detect_origins_from_urls(self):
        """
        Detect origins from URLs found in scan results.
        Looks for repository URLs, download URLs, etc.
        """
        resources_with_urls = self.project.codebaseresources.filter(
            urls__isnull=False
        ).exclude(urls=[])
        
        created_count = 0
        
        for resource in resources_with_urls:
            if hasattr(resource, 'origin_determination'):
                continue  # Skip if already has origin
            
            # Look for repository URLs
            for url_entry in resource.urls:
                url = url_entry.get("url", "")
                
                # Check if it's a repository URL
                repo_indicators = ["github.com", "gitlab.com", "bitbucket.org"]
                if any(indicator in url.lower() for indicator in repo_indicators):
                    origin = origin_utils.create_origin_from_repository(
                        resource=resource,
                        repo_url=url,
                        confidence=0.75,
                        method="url-detection"
                    )
                    if origin:
                        created_count += 1
                        break
        
        self.project.add_info(
            f"Created {created_count} origin determinations from URLs"
        )

    def detect_origins_from_repositories(self):
        """
        Detect origins from repository information if available.
        This could be extended to use git metadata or other repository signals.
        """
        # Placeholder for repository-based detection
        # Could be extended to:
        # - Read .git metadata
        # - Parse repository configuration files
        # - Use remotes information
        pass

    def calculate_confidence_scores(self):
        """
        Recalculate confidence scores based on multiple signals.
        
        This can boost confidence when multiple detection methods agree
        or when strong signals are present.
        """
        from scanpipe.models import CodeOriginDetermination
        
        origins = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project,
            is_propagated=False  # Only adjust non-propagated origins
        )
        
        adjusted_count = 0
        
        for origin in origins:
            resource = origin.codebase_resource
            
            # Boost confidence if resource has package membership
            if resource.discovered_packages.exists():
                if origin.detected_origin_confidence < 0.9:
                    origin.detected_origin_confidence = min(
                        origin.detected_origin_confidence + 0.1,
                        0.95
                    )
                    adjusted_count += 1
            
            # Boost confidence if resource has strong license signals
            if resource.detected_license_expression:
                license_count = len(resource.detected_license_expression.split(" AND "))
                if license_count >= 2 and origin.detected_origin_confidence < 0.9:
                    origin.detected_origin_confidence = min(
                        origin.detected_origin_confidence + 0.05,
                        0.95
                    )
                    adjusted_count += 1
            
            origin.save()
        
        self.project.add_info(
            f"Adjusted confidence scores for {adjusted_count} origin determinations"
        )

    def mark_high_confidence_as_verified(self):
        """
        Automatically mark very high confidence origins as verified.
        These can then be used as propagation sources.
        """
        from scanpipe.models import CodeOriginDetermination
        
        high_confidence_origins = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project,
            is_propagated=False,
            detected_origin_confidence__gte=0.9,
            is_verified=False,
        )
        
        count = high_confidence_origins.update(is_verified=True)
        
        self.project.add_info(
            f"Marked {count} high-confidence origins as verified (auto-verified)"
        )

    def propagate_origins_by_package(self):
        """
        Propagate origins based on package membership.
        Files in the same package likely share the same origin.
        """
        from scanpipe.models import CodeOriginDetermination
        
        # Get verified origins that can be propagation sources
        source_origins = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project,
            is_verified=True,
            is_propagated=False,
            detected_origin_confidence__gte=0.8,
        )
        
        total_propagated = 0
        
        for source_origin in source_origins:
            propagated = origin_utils.propagate_origin_by_package_membership(
                source_origin,
                max_targets=100
            )
            total_propagated += len(propagated)
        
        self.project.add_info(
            f"Propagated {total_propagated} origins based on package membership"
        )

    def propagate_origins_by_path(self):
        """
        Propagate origins based on path patterns and directory structure.
        Files in the same directory or with similar paths likely share origins.
        """
        from scanpipe.models import CodeOriginDetermination
        
        source_origins = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project,
            is_verified=True,
            is_propagated=False,
            detected_origin_confidence__gte=0.8,
        )
        
        total_propagated = 0
        
        for source_origin in source_origins:
            propagated = origin_utils.propagate_origin_by_path_pattern(
                source_origin,
                max_targets=50
            )
            total_propagated += len(propagated)
        
        self.project.add_info(
            f"Propagated {total_propagated} origins based on path patterns"
        )

    def propagate_origins_by_license(self):
        """
        Propagate origins based on license similarity.
        Files with similar license detection likely share origins.
        """
        from scanpipe.models import CodeOriginDetermination
        
        source_origins = CodeOriginDetermination.objects.filter(
            codebase_resource__project=self.project,
            is_verified=True,
            is_propagated=False,
            detected_origin_confidence__gte=0.8,
        )
        
        total_propagated = 0
        
        for source_origin in source_origins:
            propagated = origin_utils.propagate_origin_by_license_similarity(
                source_origin,
                threshold=0.7,
                max_targets=30
            )
            total_propagated += len(propagated)
        
        self.project.add_info(
            f"Propagated {total_propagated} origins based on license similarity"
        )

    def generate_propagation_report(self):
        """
        Generate a comprehensive report about origin detection and propagation.
        """
        # Get overall statistics
        origin_stats = origin_utils.get_origin_statistics(self.project)
        propagation_stats = origin_utils.get_propagation_statistics(self.project)
        
        # Add to project info
        self.project.add_info("=" * 50)
        self.project.add_info("ORIGIN DETERMINATION REPORT")
        self.project.add_info("=" * 50)
        
        self.project.add_info(f"Total Origins: {origin_stats['total']}")
        self.project.add_info(f"Verified Origins: {origin_stats['verified']}")
        self.project.add_info(f"Amended Origins: {origin_stats['amended']}")
        
        self.project.add_info("\nOrigins by Type:")
        for type_stat in origin_stats['by_type']:
            self.project.add_info(
                f"  - {type_stat['detected_origin_type']}: {type_stat['count']}"
            )
        
        self.project.add_info("\nConfidence Distribution:")
        self.project.add_info(f"  - High (≥0.9): {origin_stats['high_confidence_count']}")
        self.project.add_info(f"  - Medium (0.7-0.9): {origin_stats['medium_confidence_count']}")
        self.project.add_info(f"  - Low (<0.7): {origin_stats['low_confidence_count']}")
        
        self.project.add_info("\n" + "=" * 50)
        self.project.add_info("PROPAGATION STATISTICS")
        self.project.add_info("=" * 50)
        
        self.project.add_info(f"Manual Origins: {propagation_stats['manual_origins']}")
        self.project.add_info(f"Propagated Origins: {propagation_stats['propagated_origins']}")
        self.project.add_info(
            f"Propagation Rate: {propagation_stats['propagated_percentage']:.1f}%"
        )
        
        self.project.add_info("\nPropagation by Method:")
        for method_stat in propagation_stats['propagated_by_method']:
            self.project.add_info(
                f"  - {method_stat['propagation_method']}: {method_stat['count']}"
            )
        
        self.project.add_info(
            f"\nAverage Propagation Confidence: "
            f"{propagation_stats['average_propagation_confidence']:.2f}"
        )
        self.project.add_info(
            f"Verified Propagated Origins: {propagation_stats['verified_propagated_count']}"
        )


class PropagateExistingOrigins(Pipeline):
    """
    A lightweight pipeline that only performs propagation on existing origins.
    
    Use this pipeline when you already have origin determinations and want
    to propagate them to related files without re-running detection.
    """

    @classmethod
    def steps(cls):
        return (
            cls.propagate_all_origins,
            cls.generate_propagation_report,
        )

    def propagate_all_origins(self):
        """
        Run all propagation methods on existing verified origins.
        """
        stats = origin_utils.propagate_origins_for_project(
            self.project,
            methods=['package_membership', 'path_pattern', 'license_similarity'],
            min_source_confidence=0.8,
            max_targets_per_source=50
        )
        
        self.project.add_info(
            f"Propagation completed: {stats['total_propagated']} origins propagated "
            f"from {stats['source_origins_count']} sources"
        )
        
        for method, count in stats['propagated_by_method'].items():
            self.project.add_info(f"  - {method}: {count}")
        
        if stats['errors']:
            self.project.add_warning(
                f"{len(stats['errors'])} errors occurred during propagation"
            )
            for error in stats['errors'][:10]:  # Show first 10 errors
                self.project.add_warning(
                    f"  - {error['source_path']}: {error['error']}"
                )

    def generate_propagation_report(self):
        """Generate summary report."""
        propagation_stats = origin_utils.get_propagation_statistics(self.project)
        
        self.project.add_info("=" * 50)
        self.project.add_info("PROPAGATION REPORT")
        self.project.add_info("=" * 50)
        self.project.add_info(f"Total Origins: {propagation_stats['total_origins']}")
        self.project.add_info(f"Manual Origins: {propagation_stats['manual_origins']}")
        self.project.add_info(f"Propagated Origins: {propagation_stats['propagated_origins']}")
        self.project.add_info(
            f"Propagation Rate: {propagation_stats['propagated_percentage']:.1f}%"
        )
