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

  function isTypingElement(element) {
    if (!element) return false;
    const tagName = element.tagName ? element.tagName.toLowerCase() : "";
    return (
      ["input", "textarea", "select"].includes(tagName) ||
      element.isContentEditable
    );
  }

  function initSearchInteractions() {
    const searchContainer = document.getElementById('resource-search-container');
    const searchInput = document.getElementById('file-search-input');
    const searchResults = document.getElementById('search-results');
    const clearSearchBtn = document.getElementById('clear-search');
    if (!searchContainer || !searchInput || !searchResults || !clearSearchBtn) return;

    let activeIndex = -1;

    if (searchResults.parentNode !== document.body) {
      searchResults.classList.add('search-dropdown-portal');
      document.body.appendChild(searchResults);
    }

    function getResultItems() {
      return Array.from(searchResults.querySelectorAll('.search-result-item'));
    }

    function updateDropdownPosition() {
      if (searchResults.classList.contains('is-hidden')) return;

      const rect = searchContainer.getBoundingClientRect();
      const viewportPadding = 8;
      const baseWidth = Math.max(rect.width + 300, window.innerWidth * 0.5);
      const width = Math.min(baseWidth, window.innerWidth - viewportPadding * 2);
      const left = Math.max(
        viewportPadding,
        Math.min(rect.left, window.innerWidth - width - viewportPadding)
      );
      const dropdownTop = rect.bottom + 4;
      const availableHeight = window.innerHeight - dropdownTop - viewportPadding;
      const maxHeight = Math.max(180, Math.min(window.innerHeight * 0.62, availableHeight));

      searchResults.style.left = `${left}px`;
      searchResults.style.top = `${dropdownTop}px`;
      searchResults.style.width = `${width}px`;
      searchResults.style.maxHeight = `${maxHeight}px`;
    }

    function showDropdown() {
      if (searchInput.value.trim()) {
        searchResults.classList.remove('is-hidden');
        updateDropdownPosition();
      }
    }

    function hideDropdown() {
      searchResults.classList.add('is-hidden');
      setActiveItem(-1);
    }

    function updateClearButtonVisibility() {
      clearSearchBtn.classList.toggle('is-hidden', !searchInput.value.trim());
    }

    function setActiveItem(nextIndex) {
      const items = getResultItems();
      if (!items.length) {
        activeIndex = -1;
        return;
      }

      items.forEach(item => item.classList.remove('is-active'));
      if (nextIndex < 0) {
        activeIndex = -1;
        return;
      }

      activeIndex = ((nextIndex % items.length) + items.length) % items.length;
      const activeItem = items[activeIndex];
      activeItem.classList.add('is-active');
      activeItem.scrollIntoView({ block: 'nearest' });
    }

    function triggerActiveItem() {
      const items = getResultItems();
      if (!items.length) return;

      const index = activeIndex >= 0 ? activeIndex : 0;
      const activeItem = items[index];
      activeItem.click();
    }

    function clearSearch() {
      searchInput.value = '';
      updateClearButtonVisibility();
      hideDropdown();
      searchResults.innerHTML = '';
      searchInput.focus();
    }

    clearSearchBtn.addEventListener('click', clearSearch);

    searchInput.addEventListener('input', function() {
      activeIndex = -1;
      updateClearButtonVisibility();
      if (!searchInput.value.trim()) {
        hideDropdown();
      } else {
        updateDropdownPosition();
      }
    });

    searchInput.addEventListener('focus', showDropdown);

    window.addEventListener('resize', updateDropdownPosition);
    window.addEventListener('scroll', updateDropdownPosition, true);

    searchInput.addEventListener('keydown', function(event) {
      if (event.key === 'Escape') {
        hideDropdown();
        searchInput.blur();
        return;
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        const items = getResultItems();
        if (!items.length) return;
        showDropdown();
        const nextIndex = activeIndex < 0 ? 0 : activeIndex + 1;
        setActiveItem(nextIndex);
        return;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        const items = getResultItems();
        if (!items.length) return;
        showDropdown();
        const nextIndex = activeIndex < 0 ? items.length - 1 : activeIndex - 1;
        setActiveItem(nextIndex);
        return;
      }

      if (event.key === 'Enter') {
        const items = getResultItems();
        if (!items.length || searchResults.classList.contains('is-hidden')) return;
        event.preventDefault();
        triggerActiveItem();
      }
    });

    document.addEventListener('click', function(event) {
      const resultItem = event.target.closest('.search-result-item');
      if (resultItem && searchResults.contains(resultItem)) {
        hideDropdown();
        searchInput.blur();
        expandToPath(resultItem.dataset.path);
        return;
      }

      if (!searchContainer.contains(event.target) && !searchResults.contains(event.target)) {
        hideDropdown();
      }
    });

    document.addEventListener('keydown', function(event) {
      const target = event.target;
      if (event.key.toLowerCase() === 't' && !event.metaKey && !event.ctrlKey && !event.altKey) {
        if (isTypingElement(target)) return;
        event.preventDefault();
        searchInput.focus();
      }
    });

    document.body.addEventListener('htmx:afterSettle', function(event) {
      if (event.target !== searchResults) return;
      activeIndex = -1;
      updateClearButtonVisibility();
      if (searchInput.value.trim()) {
        showDropdown();
        updateDropdownPosition();
      } else {
        hideDropdown();
      }
    });

    updateClearButtonVisibility();
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

    initSearchInteractions();
  });
})();
