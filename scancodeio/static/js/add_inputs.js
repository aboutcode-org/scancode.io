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

const fileInput = document.querySelector("#id_input_files");
let selectedFiles = []; // Store selected files
let folderAlertTimeout = null;
if (fileInput) {
  fileInput.onchange = updateFiles;
}

// Update the list of files to be uploaded in the UI
function updateFiles() {
  if (fileInput && fileInput.files.length > 0) {
    const fileName = document.querySelector("#inputs_file_name");
    fileName.replaceChildren();

    // Update the selectedFiles array
    const newFiles = Array.from(fileInput.files);
    // Create a Set to track unique file names
    const uniqueFileNames = new Set(selectedFiles.map(file => file.name));
    // Filter out files with the same name
    const filteredNewFiles = newFiles.filter(file => !uniqueFileNames.has(file.name));
    // Concatenate the unique files to the existing selectedFiles array
    selectedFiles = selectedFiles.concat(filteredNewFiles);

    for (let file of selectedFiles) {
      const fileNameWithoutSpaces = file.name.replace(/\s/g, "");

      // Build the wrapper span
      const wrapper = document.createElement("span");
      wrapper.className = "is-flex is-justify-content-space-between is-block";
      wrapper.id = `file-name-${fileNameWithoutSpaces}`;

      // File name label - textContent is safe, no HTML injection possible
      const label = document.createElement("span");
      label.className = "is-block";
      label.textContent = file.name;

      // Delete button
      const deleteLink = document.createElement("a");
      deleteLink.href = "#";
      deleteLink.className = "model-button";
      deleteLink.id = `file-delete-btn-${fileNameWithoutSpaces}`;
      deleteLink.addEventListener("click", function(event) {
        disableEvent(event);
        removeFile(fileNameWithoutSpaces);
        if (selectedFiles.length == 0) {
          const emptyNotice = document.createElement("i");
          emptyNotice.textContent = "No files selected";
          fileName.replaceChildren(emptyNotice);
        }
      });

      const icon = document.createElement("i");
      icon.className = "fa-solid fa-trash-can";

      deleteLink.appendChild(icon);
      wrapper.appendChild(label);
      wrapper.appendChild(deleteLink);
      fileName.appendChild(wrapper);
    }
  }
}

// Prevent default behavior (prevent file from being opened)
function disableEvent(event) {
  event.stopPropagation();
  event.preventDefault();
}

function removeFile(fileName) {
  selectedFiles = selectedFiles.filter(file => {
    const fileNameWithoutSpaces = file.name.replace(/\s/g, "");
    return fileNameWithoutSpaces !== fileName;
  });

  const fileNameElement = document.getElementById(`file-name-${fileName}`);
  if (fileNameElement) {
    fileNameElement.remove();
  }

  const dataTransfer = new DataTransfer();
  for (let file of selectedFiles) {
    dataTransfer.items.add(file);
  }

  if (fileInput) {
    fileInput.files = dataTransfer.files;
  }
}

function inspectDataTransfer(dataTransfer) {
  const validFiles = [];
  const rejectedFolders = [];

  const items = dataTransfer.items;
  if (items && items.length > 0) {
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind !== "file") continue;

      const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
      if (entry) {
        if (entry.isDirectory) {
          rejectedFolders.push(entry.name || "folder");
          continue;
        }
      }

      const file = item.getAsFile ? item.getAsFile() : null;
      if (file) {
        validFiles.push(file);
      }
    }
  } else if (dataTransfer.files && dataTransfer.files.length > 0) {
    for (const file of dataTransfer.files) {
      validFiles.push(file);
    }
  }

  return { validFiles, rejectedFolders };
}

function showFolderUploadWarning(count) {
  const inputFilesBox = document.querySelector("#input_files_box");
  if (!inputFilesBox) return;

  const fileCta = inputFilesBox.querySelector(".file-cta");
  if (fileCta) {
    fileCta.classList.remove("has-folder-error");
    void fileCta.offsetWidth;
    fileCta.classList.add("has-folder-error");
    setTimeout(() => {
      fileCta.classList.remove("has-folder-error");
    }, 600);
  }

  if (folderAlertTimeout) {
    clearTimeout(folderAlertTimeout);
    folderAlertTimeout = null;
  }

  let tray = inputFilesBox.querySelector(".folder-notice-tray");
  let isNew = false;

  if (!tray) {
    isNew = true;
    tray = document.createElement("div");
    tray.className = "folder-notice-tray";
    tray.setAttribute("role", "alert");
    tray.setAttribute("aria-live", "polite");

    const inner = document.createElement("div");
    inner.className = "folder-notice-inner";

    const bar = document.createElement("div");
    bar.className = "folder-notice-bar";

    const main = document.createElement("div");
    main.className = "folder-notice-main";

    const iconSpan = document.createElement("span");
    iconSpan.className = "folder-notice-icon";
    const icon = document.createElement("i");
    icon.className = "fa-solid fa-folder-minus";
    iconSpan.appendChild(icon);
    main.appendChild(iconSpan);

    const msg = document.createElement("span");
    msg.className = "folder-notice-msg";
    msg.append("Folders cannot be uploaded directly. Please upload a ");

    const zipKbd = document.createElement("kbd");
    zipKbd.className = "folder-notice-kbd";
    zipKbd.textContent = ".zip";
    msg.appendChild(zipKbd);

    msg.append(" or ");

    const tarKbd = document.createElement("kbd");
    tarKbd.className = "folder-notice-kbd";
    tarKbd.textContent = ".tar.gz";
    msg.appendChild(tarKbd);

    msg.append(" archive instead.");

    const countSpan = document.createElement("span");
    countSpan.className = "folder-notice-count";
    countSpan.textContent = `(Folders skipped: ${count || 1})`;
    msg.appendChild(countSpan);

    main.appendChild(msg);

    const dismissBtn = document.createElement("button");
    dismissBtn.type = "button";
    dismissBtn.className = "folder-notice-dismiss";
    dismissBtn.setAttribute("aria-label", "Dismiss notice");
    dismissBtn.setAttribute("title", "Dismiss");
    const dismissIcon = document.createElement("i");
    dismissIcon.className = "fa-solid fa-xmark";
    dismissBtn.appendChild(dismissIcon);

    bar.appendChild(main);
    bar.appendChild(dismissBtn);
    inner.appendChild(bar);
    tray.appendChild(inner);

    inputFilesBox.appendChild(tray);
    inputFilesBox.classList.add("has-folder-notice");
  } else {
    const countSpan = tray.querySelector(".folder-notice-count");
    if (countSpan && count) {
      countSpan.textContent = `(Folders skipped: ${count})`;
    }
  }

  function dismiss() {
    if (folderAlertTimeout) {
      clearTimeout(folderAlertTimeout);
      folderAlertTimeout = null;
    }
    if (tray && tray.parentNode) {
      tray.classList.remove("is-open");
      setTimeout(() => {
        if (tray && tray.parentNode) {
          tray.remove();
        }
        if (inputFilesBox && !inputFilesBox.querySelector(".folder-notice-tray")) {
          inputFilesBox.classList.remove("has-folder-notice");
        }
      }, 230);
    }
  }

  const dismissBtn = tray.querySelector(".folder-notice-dismiss");
  if (dismissBtn) {
    dismissBtn.onclick = dismiss;
  }

  if (isNew) {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        tray.classList.add("is-open");
      });
    });
  }

  folderAlertTimeout = setTimeout(dismiss, 8000);
  tray.onmouseenter = () => {
    if (folderAlertTimeout) {
      clearTimeout(folderAlertTimeout);
      folderAlertTimeout = null;
    }
  };
  tray.onmouseleave = () => {
    folderAlertTimeout = setTimeout(dismiss, 3000);
  };
}

function dropHandler(event) {
  disableEvent(event);

  const { validFiles, rejectedFolders } = inspectDataTransfer(event.dataTransfer);

  if (rejectedFolders.length > 0) {
    showFolderUploadWarning(rejectedFolders.length);
  }

  if (validFiles.length > 0) {
    const dataTransfer = new DataTransfer();
    const existing = fileInput ? fileInput.files : [];
    for (const file of [...existing, ...validFiles]) {
      dataTransfer.items.add(file);
    }

    if (fileInput) {
      fileInput.files = dataTransfer.files;
      updateFiles();
    }
  }
}

// Handle drag and drop events
const inputFilesBox = document.querySelector("#input_files_box");
if (inputFilesBox) {
  inputFilesBox.addEventListener("dragenter", disableEvent);
  inputFilesBox.addEventListener("dragover", disableEvent);
  inputFilesBox.addEventListener("drop", dropHandler);
}
