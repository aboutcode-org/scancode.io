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

function cleanupEditor() {
  if (window.editor && window.editor.destroy) {
    window.editor.destroy();
    window.editor.container.remove();
    window.editor = null;
  }
}

function initResourceViewer(editorId) {
  const editorElement = document.getElementById(editorId);
  if (!editorElement) return;

  // Clean up previous instance if any
  cleanupEditor();

  let editor = ace.edit(editorId, {
    mode: "ace/mode/text",
    autoScrollEditorIntoView: true,
    wrap: true,
    readOnly: true,
    showPrintMargin: false,
    highlightActiveLine: false,
    highlightGutterLine: false,
    fontSize: 15,
    foldStyle: "manual",
    fontFamily: "SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace",
  });

  // Store globally for cleanup
  window.editor = editor;

  function removeAllMarkers() {
    let session = editor.getSession();
    let markers = session.getMarkers();
    for (const [key, value] of Object.entries(markers)) {
      session.removeMarker(value.id);
    }
  }

  // Range(startRow, startColumn, endRow, endColumn)
  const Range = require("ace/range").Range

  function setDetectedValues(detected_data) {
    let annotations = [];
    removeAllMarkers();

    detected_data.forEach(function($el) {
      // Indexes a 0-based in ace.js
      let start_row = $el.start_line - 1;
      let start_column = 0;
      let end_row = $el.end_line - 1;
      let end_column = 10000;

      let range = new Range(start_row, start_column, end_row, end_column);
      editor.session.addMarker(range, 'ace-marker', 'line'); // "fullLine" also available

      annotations.push({
        row: start_row,
        column: 0,
        text: $el.text,
        type: "info",
        className: $el.className,
      });

    });
    editor.getSession().setAnnotations(annotations);
  }

  let scrollPositionIndex = 0;
  const selectionButtons = getAll('#detected-data-buttons button');
  const previousBtn = document.querySelector('.previous-btn');
  const nextBtn = document.querySelector('.next-btn');

  let detected_values = JSON.parse(document.querySelector("#detected_values").textContent);
  let detected_data;

  if (selectionButtons.length > 0) {
    selectionButtons.forEach(function($el) {
      $el.addEventListener('click', function() {
        removeAllMarkers();
        let active_button = document.querySelector("#detected-data-buttons button.is-info");
        if (active_button) active_button.classList.remove("is-info");

        $el.classList.add("is-info");
        let type = $el.getAttribute("data-type");
        detected_data = detected_values[type];

        if (detected_data.length) {
          scrollPositionIndex = 0;
          setDetectedValues(detected_data);
          editor.renderer.scrollToLine(detected_data[0].start_line - 1);
          previousBtn.disabled = true;
          nextBtn.disabled = detected_data.length - 1 === 0;
        } else {
          scrollPositionIndex = 0;
          editor.renderer.scrollToLine(0);
          previousBtn.disabled = true;
          nextBtn.disabled = true;
        }
      });
    });
  }

  nextBtn.addEventListener('click', function() {
    if (scrollPositionIndex >= detected_data.length - 1) return false;
    scrollPositionIndex++;
    editor.renderer.scrollToLine(detected_data[scrollPositionIndex].start_line - 1);
    nextBtn.disabled = scrollPositionIndex === detected_data.length - 1;
    previousBtn.disabled = false;
  });

  previousBtn.addEventListener('click', function() {
    if (scrollPositionIndex <= 0) return false;
    scrollPositionIndex--;
    editor.renderer.scrollToLine(detected_data[scrollPositionIndex].start_line - 1);
    previousBtn.disabled = scrollPositionIndex === 0;
    nextBtn.disabled = false;
  });

  const fullscreenBtn = document.querySelector('#toggle-fullscreen');
  fullscreenBtn.addEventListener('click', function() {
    let body = document.querySelector('body');
    let is_full_screen = body.classList.toggle("full-screen");
    editor.resize()
  });
}

// Init on page load if editor is present
initResourceViewer('editor');

// Re-initialize the editor when new content is loaded via htmx
document.addEventListener('htmx:afterSettle', function(event) {
  if (event.detail.target.querySelector('#editor')) {
    initResourceViewer('editor');
  }
});
