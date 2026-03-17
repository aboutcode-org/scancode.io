// SPDX-License-Identifier: Apache-2.0
//
// http://nexb.com and https://github.com/aboutcode-org/scancode.io
// The ScanCode.io software is licensed under the Apache License version 2.0.
// Data generated with ScanCode.io is provided as-is without warranties.
// ScanCode is a trademark of nexB Inc.
//
// You may not use this software except in compliance with the License.
// You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software distributed
// under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//
// Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, either express or implied. No content created from
// ScanCode.io should be considered or used as legal advice. Consult an Attorney
// for any legal advice.
//
// ScanCode.io is a free software code scanning tool from nexB Inc. and others.
// Visit https://github.com/aboutcode-org/scancode.io for support and download.

'use strict';

(function() {
  const form = document.querySelector('form');
  if (!form) return;

  const pipelineSelect = document.getElementById("id_pipeline");
  if (!pipelineSelect) return;

  // Upload progress overlay on form submit
  form.addEventListener('submit', function(event) {
    let background = displayOverlay();

    // The upload progress is only added when input files are provided.
    if (!form["input_files"].files.length) return false;

    event.preventDefault();

    let progress_bar = document.createElement('progress');
    progress_bar.className = 'progress is-success is-medium file-upload';
    progress_bar.setAttribute('value', '0');
    progress_bar.setAttribute('max', '100');

    let progress_container = document.createElement('div');
    progress_container.className = 'container is-max-desktop mt-6 px-6';
    progress_container.appendChild(progress_bar)
    background.appendChild(progress_container);

    let form_errors = document.getElementById('form-errors');
    displayFormUploadProgress(form, progress_bar, form_errors, true);
  });

  // Pipeline groups checkboxes

  const availableGroupsDataSource = document.getElementById("pipelines_available_groups");
  if (!availableGroupsDataSource) return;

  const availableGroupsMapping = JSON.parse(availableGroupsDataSource.textContent);
  const idSelectedGroups = document.getElementById("id_selected_groups");

  function clearSelectedGroups() {
    idSelectedGroups.replaceChildren();
  }

  function buildCheckbox(group) {
    const id = `id_${group}`;
    const label = document.createElement('label');
    label.className = 'checkbox ml-1 mb-1';
    label.htmlFor = id;

    const span = document.createElement('span');
    span.className = 'tag is-warning has-text-weight-bold';

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = 'selected_groups';
    input.value = group;
    input.id = id;
    input.className = 'mr-1';

    span.appendChild(input);
    span.appendChild(document.createTextNode(' ' + group));

    label.appendChild(span);

    return label;
  }

  function handlePipelineChange() {
    clearSelectedGroups();

    const selectedPipelineName = pipelineSelect.value;
    if (!selectedPipelineName) return;

    const availableGroups = availableGroupsMapping[selectedPipelineName];
    if (availableGroups && availableGroups.length > 0) {
      const strongElement = document.createElement('strong');
      const icon = document.createElement('i');
      icon.className = 'fa-solid fa-circle-arrow-right';
      strongElement.appendChild(icon);
      strongElement.appendChild(document.createTextNode(' Include:'));
      idSelectedGroups.appendChild(strongElement);

      availableGroups.forEach((group) => {
        const checkboxElement = buildCheckbox(group);
        idSelectedGroups.appendChild(checkboxElement);
      });
    }
  }

  handlePipelineChange();
  pipelineSelect.addEventListener("change", handlePipelineChange);

  // Auto-detect pipeline from input value

  function detectPipelineFromValue(value) {
    value = value.trim().toLowerCase();

    if (!value) return "";

    // Handle Docker reference
    if (value.startsWith("docker:")) return "analyze_docker_image";

    // Handle Package URL
    if (value.startsWith("pkg:")) return "scan_single_package";

    // Handle SBOM file formats
    if (
      value.endsWith(".spdx") ||
      value.endsWith(".spdx.json") ||
      value.endsWith(".spdx.yml") ||
      value.endsWith("bom.json") ||
      value.endsWith(".cdx.json") ||
      value.endsWith(".cyclonedx.json") ||
      value.endsWith("bom.xml") ||
      value.endsWith(".cdx.xml") ||
      value.endsWith(".cyclonedx.xml")
    ) return "load_sbom";

    // No match
    return "";
  }

  const textarea = document.getElementById("id_input_urls");
  const fileInput = document.getElementById("id_input_files");

  // Handle textarea input
  textarea.addEventListener("input", () => {
    const value = textarea.value.trim();
    const pipeline = detectPipelineFromValue(value);
    pipelineSelect.value = pipeline;
  });

  // Handle file uploads
  fileInput.addEventListener("change", () => {
    const files = Array.from(fileInput.files);

    // Detect based on first file, multiple input files not supported.
    if (files.length === 1) {
      const firstFile = files[0].name.toLowerCase();
      const pipeline = detectPipelineFromValue(firstFile);
      pipelineSelect.value = pipeline;
    } else {
      pipelineSelect.value = "";
    }
  });

})();