//
// Selected parts from https://bulma.io/lib/main.js?v=202104191409
//

'use strict';

let rootEl = document.documentElement;

// Modals

// Opens that `target` modal
function openModal(target) {
  var $target = document.getElementById(target);
  rootEl.classList.add('is-clipped');
  $target.classList.add('is-active');
}

// Close all modals
function closeModals() {
  var $modals = getAll('.modal');

  rootEl.classList.remove('is-clipped');
  $modals.forEach(function ($el) {
    $el.classList.remove('is-active');
  });
}

// Setup modal buttons to open the related modal on click
function setupOpenModalButtons() {
  var $modalButtons = getAll('.modal-button');

  if ($modalButtons.length > 0) {
    $modalButtons.forEach(function ($el) {
      $el.addEventListener('click', function () {
        var target = $el.dataset.target;
        // Fire a custom event on opening a Modal
        document.dispatchEvent(new CustomEvent("openModal", {
          detail: {modal: target, $button: $el}
        }));
        openModal(target);
      });
    });
  }
}

// Setup modal close buttons to close modals on click
// The "is-no-close" class can be used to bypass the close behavior
function setupCloseModalButtons() {
  var $modalCloses = getAll('.modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button');

  if ($modalCloses.length > 0) {
    $modalCloses.forEach(function ($el) {
      if ($el.classList.contains('is-no-close')) return;
      $el.addEventListener('click', function () {
        closeModals();
      });
    });
  }
}

// Utils, available globally

function getAll(selector) {
  var parent = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : document;
  return Array.prototype.slice.call(parent.querySelectorAll(selector), 0);
}

function displayOverlay() {
  let background = document.createElement("div");
  background.className = "modal-background";
  background.style.cssText = "z-index:100;color:white;text-align:center;padding-top:150px;position:fixed;";
  background.innerHTML = '<div class="fa-5x"><i class="fas fa-circle-notch fa-spin"></i></div>';
  document.body.appendChild(background);
}


document.addEventListener('DOMContentLoaded', function () {

  setupOpenModalButtons();
  setupCloseModalButtons();

  // Close modals and dropdowns on pressing "escape" key
  document.addEventListener('keydown', function (event) {
    var e = event || window.event;

    if (e.keyCode === 27) {
      closeModals();
      closeDropdowns();
    }
  });

  // Dropdowns

  var $dropdowns = getAll('.dropdown:not(.is-hoverable)');

  if ($dropdowns.length > 0) {
    $dropdowns.forEach(function ($el) {
      $el.addEventListener('click', function (event) {
        event.stopPropagation();
        $el.classList.toggle('is-active');
      });
    });

    document.addEventListener('click', function (event) {
      closeDropdowns();
    });
  }

  function closeDropdowns() {
    $dropdowns.forEach(function ($el) {
      $el.classList.remove('is-active');
    });
  }

});
