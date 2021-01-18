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

from django.urls import path

from scanpipe import views

urlpatterns = [
    path(
        "project/<uuid:uuid>/resources/",
        views.CodebaseResourceListView.as_view(),
        name="project_resources",
    ),
    path(
        "project/<uuid:uuid>/packages/",
        views.DiscoveredPackageListView.as_view(),
        name="project_packages",
    ),
    path(
        "project/<uuid:uuid>/errors/",
        views.ProjectErrorListView.as_view(),
        name="project_errors",
    ),
    path(
        "project/<uuid:uuid>/tree/",
        views.ProjectTreeView.as_view(),
        name="project_tree",
    ),
    path(
        "project/<uuid:uuid>/delete/",
        views.ProjectDeleteView.as_view(),
        name="project_delete",
    ),
    path(
        "project/<uuid:uuid>/results/<path:format>/",
        views.ProjectResultsView.as_view(),
        name="project_results",
    ),
    path(
        "project/add/",
        views.ProjectCreateView.as_view(),
        name="project_add",
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
]
