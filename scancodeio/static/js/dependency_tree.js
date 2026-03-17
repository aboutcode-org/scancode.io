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
  const treeContainer = document.getElementById('tree');
  const collapseAllButton = document.getElementById('collapseAll');
  const expendAllButton = document.getElementById('expendAll');

  if (!collapseAllButton) return;

  function collapseAllDetails() {
    document.querySelectorAll('details').forEach(details => {
      details.removeAttribute('open');
    });
    showAllListItems();
  }

  function expendAllDetails() {
    document.querySelectorAll('details').forEach(details => {
      details.setAttribute('open', ''); // Adding 'open' attribute to open the details
    });
    showAllListItems();
  }

  collapseAllButton.addEventListener('click', collapseAllDetails);
  expendAllButton.addEventListener('click', expendAllDetails);

  // Following function are use to limit the display to specific elements.

  function expandAncestors(detailsElement) {
    let parent = detailsElement.parentElement.closest('details');
    while (parent) {
      parent.setAttribute('open', '');
      parent.parentElement.style.display = '';
      parent = parent.parentElement.closest('details');
    }
  }

  function showAllListItems() {
    const listItems = treeContainer.querySelectorAll('li');
    listItems.forEach(item => {
        item.style.display = '';
    });
  }

  function hideAllListItems() {
    const listItems = treeContainer.querySelectorAll('li');
    listItems.forEach(item => {
        item.style.display = 'none';
    });
  }

  function handleItems(attribute, value) {
    collapseAllDetails();
    hideAllListItems();

    const items = document.querySelectorAll(`li[${attribute}="${value}"]`);
    items.forEach(item => {
        item.style.display = 'block';
        expandAncestors(item);
    });
  }

  function handleVulnerableItems() {
    handleItems('data-is-vulnerable', 'true');
  }

  function handleComplianceAlertItems() {
    handleItems('data-compliance-alert', 'true');
  }

  showVulnerableOnlyButton.addEventListener('click', handleVulnerableItems);
  showComplianceAlertOnlyButton.addEventListener('click', handleComplianceAlertItems);
})();
