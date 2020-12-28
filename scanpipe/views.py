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

from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView

from scanpipe.api.serializers import scanpipe_app_config
from scanpipe.forms import ProjectForm
from scanpipe.models import Project
from scanpipe.pipelines import get_pipeline_doc
from scanpipe.pipes import codebase


class ProjectListView(ListView):
    model = Project
    template_name = "scanpipe/project_list.html"


class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    success_url = reverse_lazy("project_list")
    template_name = "scanpipe/project_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["pipelines"] = [
            {
                "location": location,
                "name": name,
                "description": get_pipeline_doc(location),
            }
            for location, name in scanpipe_app_config.pipelines
        ]

        return context


class ProjectTreeView(DetailView):
    model = Project
    slug_url_kwarg = "uuid"
    slug_field = "uuid"
    template_name = "scanpipe/project_tree.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        fields = ["name", "path"]
        project_codebase = codebase.ProjectCodebase(self.object)
        context["tree_data"] = [codebase.get_tree(project_codebase.root, fields)]

        return context
