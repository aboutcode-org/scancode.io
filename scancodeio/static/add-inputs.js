// SPDX-License-Identifier: Apache-2.0
//
// http://nexb.com and https://github.com/nexB/scancode.io
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
// Visit https://github.com/nexB/scancode.io for support and download.

const fileInput = document.querySelector('#id_input_files');
fileInput.onchange = update_files;

const input_urls = document.querySelector('#id_input_urls');
input_urls.oninput = () => {
  input_urls.style.height = "";
  input_urls.style.height = input_urls.scrollHeight + 3 + "px";
}

// Handling DropZone Events
const dropzone = document.querySelector('#file_upload_label');
dropzone.addEventListener("dragenter", disable_event);
dropzone.addEventListener("dragover", disable_event);
dropzone.addEventListener("drop", dropHandler);

function disable_event(e) {
  e.stopPropagation();
  e.preventDefault();
}

function dropHandler(event) {
  // Prevent default behavior (Prevent file from being opened)
  disable_event(event);
  document.querySelector('#id_input_files').files = event.dataTransfer.files;
  update_files();
}

// Function for updating file_names in span
function update_files() {
  if (fileInput.files.length > 0) {
    const fileName = document.querySelector('#inputs-file-name');
    fileName.innerHTML = "";
    for (file of fileInput.files) {
      fileName.innerHTML += `<span class="is-block">${file.name}</span>`;
    }
  }
}
