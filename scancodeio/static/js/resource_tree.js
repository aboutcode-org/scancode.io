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
  async function toggleFolderNode(folderNode, forceExpand = false) {
    const targetId = folderNode.dataset.target;
    const url = folderNode.dataset.url;
    const target = document.getElementById("dir-" + targetId);
    const chevron = folderNode.querySelector("[data-chevron]");

    if (!target || !chevron) return;

    if (target.dataset.loaded === "true") {
      if (forceExpand) {
        target.classList.remove("is-hidden");
        chevron.classList.add("rotated");
      } else {
        target.classList.toggle("is-hidden");
        chevron.classList.toggle("rotated");
      }
    } else {
      target.classList.remove("is-hidden");
      const fullUrl = new URL(url, window.location.origin);
      fullUrl.searchParams.append('tree_panel', 'true');
      const response = await fetch(fullUrl.toString());
      target.innerHTML = await response.text();
      target.dataset.loaded = "true";
      htmx.process(target);
      chevron.classList.add("rotated");
    }
  }

  async function expandToPath(path) {
    const parts = path.split('/').filter(Boolean);
    let current = "";
    for (const part of parts) {
      current = current ? current + "/" + part : part;
      const folderNode = document.querySelector(`[data-folder][data-path="${current}"]`);
      if (folderNode) await toggleFolderNode(folderNode, true);
    }
    const finalNode = document.querySelector(`[data-folder][data-path="${path}"], .is-file[data-file][data-path="${path}"]`);
    if (finalNode) {
      document.querySelectorAll('.is-current').forEach(el => el.classList.remove('is-current'));
      finalNode.classList.add('is-current');
      finalNode.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  document.addEventListener("click", async e => {
    const node = e.target.closest("[data-folder], .is-file[data-file], .expand-in-tree, [data-chevron]");
    if (!node) return;

    e.preventDefault();
    if (node.matches("[data-chevron]")) {
      await toggleFolderNode(node.closest("[data-folder]"));
    } else if (node.matches("[data-folder], .is-file[data-file], .expand-in-tree")) {
      await expandToPath(node.dataset.path);
    }
  });

  document.addEventListener("DOMContentLoaded", function() {
    const container = document.getElementById('resource-tree-container');
    if (!container) return;

    const currentPath = container.dataset.currentPath;
    if (currentPath) {
      expandToPath(currentPath);
    }

    const resizer = document.getElementById('resizer');
    const leftPane = document.getElementById('left-pane');
    const rightPane = document.getElementById('right-pane');
    let isResizing = false;

    resizer.addEventListener('mousedown', function(e) {
      isResizing = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
      if (!isResizing) return;

      const container = document.querySelector('.resizable-container');
      const containerRect = container.getBoundingClientRect();
      let newLeftWidth = e.clientX - containerRect.left;
      const containerWidth = containerRect.width;
      const resizerWidth = 5;
      const minLeftWidth = 200;
      if (newLeftWidth < minLeftWidth) newLeftWidth = minLeftWidth;
      if (newLeftWidth > containerWidth - resizerWidth) newLeftWidth = containerWidth - resizerWidth;

      const leftPercent = (newLeftWidth / containerWidth) * 100;
      const rightPercent = ((containerWidth - newLeftWidth - resizerWidth) / containerWidth) * 100;

      leftPane.style.flexBasis = leftPercent + '%';
      rightPane.style.flexBasis = rightPercent + '%';
    });

    document.addEventListener('mouseup', function() {
      if (isResizing) {
        isResizing = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    });

    // Show/hide left pane
    const hidePaneButton = document.getElementById('hide-left-pane');
    hidePaneButton.addEventListener('click', function() {
      leftPane.classList.add('is-hidden');
      resizer.classList.add('is-hidden');

      const expandPaneButton = document.getElementById('expand-left-pane');
      expandPaneButton.classList.remove('is-hidden');
      expandPaneButton.addEventListener('click', function() {
        leftPane.classList.remove('is-hidden');
        resizer.classList.remove('is-hidden');
        expandPaneButton.classList.add('is-hidden');
      });
    });

  });
})();