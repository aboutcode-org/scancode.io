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

// Tabs

function setupTabs() {
  const $tabLinks = getAll('.tabs a');

  function activateTab($tabLink) {
    const activeLink = document.querySelector('.tabs .is-active');
    const activeTabContent = document.querySelector('.tab-content.is-active');
    const targetId = $tabLink.dataset.target;
    const targetTabContent = document.getElementById(targetId);

    activeLink.classList.remove('is-active');
    $tabLink.parentNode.classList.add('is-active');
    if (activeTabContent) activeTabContent.classList.remove('is-active');
    if (targetTabContent) targetTabContent.classList.add('is-active');

    // Set the active tab in the URL hash. The "tab-" prefix is removed to avoid
    // un-wanted scrolling to the related "id" element
    document.location.hash = targetId.replace('tab-', '');
  }

  // Activate the related tab if hash is present in URL
  if (document.location.hash !== "") {
    let tabName = document.location.hash.slice(1);
    let tabLink = document.querySelector(`a[data-target="tab-${tabName}"]`);
    if (tabLink) activateTab(tabLink);
  }

  $tabLinks.forEach(function ($el) {
    $el.addEventListener('click', function () {
      activateTab($el)
    });
  });
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
  return background;
}

// Display and update the `$progress` object on `$form` submitted using XHR
function displayFormUploadProgress($form, $progress, $form_errors) {

 // Prepare an AJAX request to submit the form and track the progress
  let xhr = new XMLHttpRequest();

  // Submit the form using initial form attributes
  xhr.open($form.getAttribute('method'), $form.getAttribute('action'), true);
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

  xhr.upload.addEventListener('progress', function(event) {
    console.log("XHR progress event fired");
    // Compute the progress percentage and set the value on the `progress` element
    if (event.lengthComputable) {
      let percent = (event.loaded / event.total * 100).toFixed();
      $progress.setAttribute('value', percent);
    }
  }, false);

  xhr.addEventListener('readystatechange', function(event) {
    let target = event.target;
    console.log("XHR readystatechange event fired");

    if (target.readyState === XMLHttpRequest.DONE) {
      if (target.status === 201) {
        let response_json = JSON.parse(target.response);
        window.location.replace(response_json['redirect_url']);
      }
      else if (target.status === 400) {
        let response_json = JSON.parse(target.response);
        $form_errors.innerHTML = response_json['errors'];
        $form_errors.classList.remove("is-hidden");
        // Remove the background
        $progress.parentNode.parentNode.remove();
      }
      else {
        throw new Error('Error.');
      }
    }
  }, false);

  xhr.send(new FormData($form));
}

document.addEventListener('DOMContentLoaded', function () {

  setupOpenModalButtons();
  setupCloseModalButtons();
  setupTabs();

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

// Toasts (requires bulma-toast.js)

function displayPipelineStatusToast(run_status, pipeline_name, project_url) {
    const default_options = {
      "position": "top-center",
      "dismissible": true,
      "closeOnClick": false,
      "pauseOnHover": true,
      "duration": 30000 // 30 secs
    }
    let custom_options;

    if (run_status === "running") {
      custom_options = {
        "message": `Pipeline ${pipeline_name} started.`,
        "type": "is-info",
        "duration": 3000 // 3 secs
      }
    }
    else if (run_status === "success") {
      custom_options = {
        "message": `Pipeline ${pipeline_name} completed successfully.\n` +
                   `<a href="${project_url}">Access or refresh the project page for results.</a>`,
        "type": "is-success is-inline-block",
      }
    }
    else {
      custom_options = {
        "message": `Pipeline ${pipeline_name} ${run_status}.`,
        "type": "is-danger",
      }
    }

    bulmaToast.toast({...default_options, ...custom_options});
}
