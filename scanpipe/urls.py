# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

from django.urls import include
from django.urls import path

from scanpipe import views

urlpatterns = [
    path(
        "project/<uuid:uuid>/resources/<path:path>/raw/",
        views.CodebaseResourceRawView.as_view(),
        name="resource_raw",
    ),
    path(
        "project/<uuid:uuid>/resources/<path:path>/",
        views.CodebaseResourceDetailsView.as_view(),
        name="resource_detail",
    ),
    path(
        "project/<uuid:uuid>/resources/",
        views.CodebaseResourceListView.as_view(),
        name="project_resources",
    ),
    path(
        "project/<uuid:uuid>/packages/<int:pk>/",
        views.DiscoveredPackageDetailsView.as_view(),
        name="package_detail",
    ),
    path(
        "project/<uuid:uuid>/dependencies/<int:pk>/",
        views.DiscoveredDependencyDetailsView.as_view(),
        name="dependency_detail",
    ),
    path(
        "project/<uuid:uuid>/packages/",
        views.DiscoveredPackageListView.as_view(),
        name="project_packages",
    ),
    path(
        "project/<uuid:uuid>/dependencies/",
        views.DiscoveredDependencyListView.as_view(),
        name="project_dependencies",
    ),
    path(
        "project/<uuid:uuid>/errors/",
        views.ProjectErrorListView.as_view(),
        name="project_errors",
    ),
    path(
        "project/<uuid:uuid>/archive/",
        views.ProjectArchiveView.as_view(),
        name="project_archive",
    ),
    path(
        "project/<uuid:uuid>/delete/",
        views.ProjectDeleteView.as_view(),
        name="project_delete",
    ),
    path(
        "project/<uuid:uuid>/reset/",
        views.ProjectResetView.as_view(),
        name="project_reset",
    ),
    path(
        "run/<uuid:uuid>/",
        views.run_detail_view,
        name="run_detail",
    ),
    path(
        "run/<uuid:uuid>/status/",
        views.run_status_view,
        name="run_status",
    ),
    path(
        "project/<uuid:uuid>/results/<path:format>/",
        views.ProjectResultsView.as_view(),
        name="project_results",
    ),
    path(
        "project/<uuid:uuid>/execute_pipeline/<uuid:run_uuid>/",
        views.execute_pipeline_view,
        name="project_execute_pipeline",
    ),
    path(
        "project/<uuid:uuid>/stop_pipeline/<uuid:run_uuid>/",
        views.stop_pipeline_view,
        name="project_stop_pipeline",
    ),
    path(
        "project/<uuid:uuid>/delete_pipeline/<uuid:run_uuid>/",
        views.delete_pipeline_view,
        name="project_delete_pipeline",
    ),
    path(
        "project/add/",
        views.ProjectCreateView.as_view(),
        name="project_add",
    ),
    path(
        "project/<uuid:uuid>/charts/",
        views.ProjectChartsView.as_view(),
        name="project_charts",
    ),
    path(
        "project/<uuid:uuid>/",
        views.ProjectDetailView.as_view(),
        name="project_detail",
    ),
    path(
        "project/",
        views.ProjectListView.as_view(),
        name="project_list",
    ),
    path("monitor/", include("django_rq.urls")),
]
