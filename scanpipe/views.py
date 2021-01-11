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

from collections import Counter

from django.db.models import Q
from django.http import FileResponse
from django.http import Http404
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView

from scanpipe import pipelines
from scanpipe.api.serializers import scanpipe_app_config
from scanpipe.forms import ProjectForm
from scanpipe.models import Project
from scanpipe.pipes import codebase
from scanpipe.pipes import outputs


class ProjectListView(ListView):
    model = Project
    template_name = "scanpipe/project_list.html"


class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "scanpipe/project_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pipelines"] = [
            {
                "location": location,
                "name": name,
                "description": pipelines.get_pipeline_doc(location),
                "steps": pipelines.get_pipeline_steps(location),
            }
            for location, name in scanpipe_app_config.pipelines
        ]
        return context

    def get_success_url(self):
        return reverse("project_detail", kwargs={"uuid": self.object.pk})


class ProjectDetailView(DetailView):
    model = Project
    slug_url_kwarg = "uuid"
    slug_field = "uuid"
    template_name = "scanpipe/project_detail.html"

    @staticmethod
    def get_summary(values_list, limit=6):
        most_common = dict(Counter(values_list).most_common(limit))

        other = len(values_list) - sum(most_common.values())
        if other > 0:
            most_common["Other"] = other

        # Set a label for empty string value and move to last entry in the dict
        if "" in most_common:
            most_common["(No value detected)"] = most_common.pop("")

        return most_common

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resources_qs_base = self.object.codebaseresources.all()
        resources_qs = resources_qs_base.only(
            "programming_language",
            "mime_type",
            "holders",
            "copyrights",
            "license_expressions",
        )
        package_orphans_qs = resources_qs_base.package_orphans()
        packages_qs = self.object.discoveredpackages.all().only(
            "type",
            "license_expression",
        )

        programming_languages = resources_qs.values_list(
            "programming_language", flat=True
        )
        mime_types = resources_qs.values_list("mime_type", flat=True)
        holders = [
            holder.get("value")
            for holders in resources_qs.values_list("holders", flat=True)
            for holder in holders
        ]
        licenses = [
            license.get("key")
            for licenses in resources_qs.values_list("licenses", flat=True)
            for license in licenses
        ]

        package_orphans = {
            "Licenses and Copyrights": package_orphans_qs.filter(
                ~Q(license_expressions=[]), ~Q(copyrights=[])
            ).count(),
            "Licenses": package_orphans_qs.filter(
                ~Q(license_expressions=[]), copyrights=[]
            ).count(),
            "Copyrights": package_orphans_qs.filter(
                ~Q(copyrights=[]), license_expressions=[]
            ).count(),
            "(No value detected)": package_orphans_qs.filter(
                license_expressions=[], copyrights=[]
            ).count(),
        }

        package_licenses = packages_qs.values_list("license_expression", flat=True)
        package_types = packages_qs.values_list("type", flat=True)

        context.update(
            {
                "programming_languages": self.get_summary(programming_languages),
                "mime_types": self.get_summary(mime_types),
                "holders": self.get_summary(holders),
                "licenses": self.get_summary(licenses),
                "package_orphans": package_orphans,
                "package_licenses": self.get_summary(package_licenses),
                "package_types": self.get_summary(package_types),
            }
        )
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


def project_results_json_response(project, as_attachment=False):
    """
    Return the results as JSON compatible with ScanCode data format.
    The content is returned as a stream of JSON content using the JSONResultsGenerator
    class.
    If `as_attachment` is True, the response will force the download of the file.
    """
    results_generator = outputs.JSONResultsGenerator(project)
    response = FileResponse(
        streaming_content=results_generator,
        content_type="application/json",
    )

    if as_attachment:
        response["Content-Disposition"] = f'attachment; filename="{project.name}.json"'

    return response


class ProjectResultsView(DetailView):
    model = Project
    slug_url_kwarg = "uuid"
    slug_field = "uuid"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        project = self.object
        format = self.kwargs["format"]

        if format == "json":
            return project_results_json_response(project, as_attachment=True)

        elif format == "xlsx":
            output_file = outputs.to_xlsx(project)
            filename = f"{project.name}_{output_file.name}"
            return FileResponse(output_file.open("rb"), filename=filename)

        raise Http404("Format not supported.")
