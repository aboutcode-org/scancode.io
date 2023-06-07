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
fileInput.onchange = updateFiles;

// Update the list of files to be uploaded in the UI
function updateFiles() {
  if (fileInput.files.length > 0) {
    const fileName = document.querySelector('#inputs_file_name');
    fileName.innerHTML = "";
    for (let file of fileInput.files) {
      fileName.innerHTML += `<span class="is-block">${file.name}</span>`;
    }
  }
}

// Prevent default behavior (prevent file from being opened)
function disableEvent(event) {
  event.stopPropagation();
  event.preventDefault();
}

function dropHandler(event) {
  disableEvent(event);
  const droppedFiles = event.dataTransfer.files;
  const updatedFiles = Array.from(fileInput.files);

  for (let file of droppedFiles) {
    updatedFiles.push(file);
  }
  
  const dataTransfer = new DataTransfer();
  for (let file of updatedFiles) {
    dataTransfer.items.add(file);
  }
  
  fileInput.files = dataTransfer.files;
  updateFiles();
}

// Handle drag and drop events
const inputFilesBox = document.querySelector('#input_files_box');
inputFilesBox.addEventListener("dragenter", disableEvent);
inputFilesBox.addEventListener("dragover", disableEvent);
inputFilesBox.addEventListener("drop", dropHandler);
