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

from scanpipe.management.commands import ProjectCommand
from scanpipe import origin_utils


class Command(ProjectCommand):
    help = (
        "Propagate verified origin determinations to similar/related files. "
        "Uses package membership, path patterns, and license similarity as signals."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        
        parser.add_argument(
            "--methods",
            nargs="+",
            choices=["package_membership", "path_pattern", "license_similarity"],
            default=["package_membership", "path_pattern", "license_similarity"],
            help="Propagation methods to use (default: all methods)",
        )
        
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.8,
            help="Minimum confidence for source origins (default: 0.8)",
        )
        
        parser.add_argument(
            "--max-targets",
            type=int,
            default=50,
            help="Maximum targets per source origin (default: 50)",
        )
        
        parser.add_argument(
            "--report",
            action="store_true",
            help="Show detailed propagation report",
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        
        methods = options["methods"]
        min_confidence = options["min_confidence"]
        max_targets = options["max_targets"]
        show_report = options["report"]
        
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Propagating origins for project: {self.project.name}"
            )
        )
        
        self.stdout.write(f"Methods: {', '.join(methods)}")
        self.stdout.write(f"Min confidence: {min_confidence}")
        self.stdout.write(f"Max targets per source: {max_targets}")
        self.stdout.write("")
        
        # Run propagation
        try:
            stats = origin_utils.propagate_origins_for_project(
                self.project,
                methods=methods,
                min_source_confidence=min_confidence,
                max_targets_per_source=max_targets,
            )
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Propagation completed successfully"
                )
            )
            self.stdout.write("")
            
            self.stdout.write(
                f"Source origins used: {stats['source_origins_count']}"
            )
            self.stdout.write(
                f"Total propagated: {stats['total_propagated']}"
            )
            
            if stats['propagated_by_method']:
                self.stdout.write("\nPropagated by method:")
                for method, count in stats['propagated_by_method'].items():
                    self.stdout.write(f"  - {method}: {count}")
            
            if stats['errors']:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ {len(stats['errors'])} errors occurred"
                    )
                )
                # Show first 5 errors
                for error in stats['errors'][:5]:
                    self.stdout.write(
                        f"  - {error['source_path']}: {error['error']}"
                    )
                if len(stats['errors']) > 5:
                    self.stdout.write(
                        f"  ... and {len(stats['errors']) - 5} more errors"
                    )
            
            # Show detailed report if requested
            if show_report:
                self.stdout.write("")
                self.stdout.write(
                    self.style.MIGRATE_HEADING("DETAILED PROPAGATION REPORT")
                )
                self.stdout.write("")
                
                prop_stats = origin_utils.get_propagation_statistics(self.project)
                origin_stats = origin_utils.get_origin_statistics(self.project)
                
                self.stdout.write("Origin Statistics:")
                self.stdout.write(f"  Total origins: {origin_stats['total']}")
                self.stdout.write(f"  Verified: {origin_stats['verified']}")
                self.stdout.write(f"  Amended: {origin_stats['amended']}")
                self.stdout.write(
                    f"  Average confidence: {origin_stats['average_confidence']:.2f}"
                )
                
                self.stdout.write("\nPropagation Statistics:")
                self.stdout.write(
                    f"  Manual origins: {prop_stats['manual_origins']}"
                )
                self.stdout.write(
                    f"  Propagated origins: {prop_stats['propagated_origins']}"
                )
                self.stdout.write(
                    f"  Propagation rate: {prop_stats['propagated_percentage']:.1f}%"
                )
                self.stdout.write(
                    f"  Avg propagation confidence: "
                    f"{prop_stats['average_propagation_confidence']:.2f}"
                )
                self.stdout.write(
                    f"  Verified propagated: {prop_stats['verified_propagated_count']}"
                )
                
                if prop_stats['propagated_by_method']:
                    self.stdout.write("\n  Propagated by method:")
                    for method_stat in prop_stats['propagated_by_method']:
                        self.stdout.write(
                            f"    - {method_stat['propagation_method']}: "
                            f"{method_stat['count']}"
                        )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Propagation failed: {str(e)}")
            )
            raise
