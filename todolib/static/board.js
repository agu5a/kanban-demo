// Board behaviour, loaded with `defer` from the page; no library, no inline script.
// - New todo dialog: "New todo" opens it, Cancel and Escape (native <dialog>) close it without a request.
// - Drag and drop: an item dropped on another column is moved with POST /move, then the page reloads to show the
//   server's state; on an error the item stays and the server's text is shown in an alert above the columns.

function _setInvalid(input, message) {
  input.classList.add("is-invalid");
  let feedback = input.nextElementSibling;
  if (!feedback || !feedback.classList.contains("invalid-feedback")) {
    feedback = document.createElement("div");
    feedback.className = "invalid-feedback";
    input.after(feedback);
  }
  feedback.textContent = message;
}

function _clearInvalid(input) {
  input.classList.remove("is-invalid");
  const feedback = input.nextElementSibling;
  if (feedback && feedback.classList.contains("invalid-feedback")) {
    feedback.remove();
  }
}

function _validateForm(form) {
  const errors = [];
  const titleInput = form.querySelector('[name="title"]');
  const labelsInput = form.querySelector('[name="labels"]');
  const assigneeInput = form.querySelector('[name="assignee"]');

  _clearInvalid(titleInput);
  _clearInvalid(labelsInput);
  if (assigneeInput) {
    _clearInvalid(assigneeInput);
  }

  if (!titleInput.value.trim()) {
    errors.push([titleInput, "title must not be empty"]);
  }

  const parts = labelsInput.value
    .split(",")
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
  for (const part of parts) {
    if (!/^[a-z0-9-]{1,20}$/i.test(part)) {
      errors.push([labelsInput, `invalid label: ${part}`]);
      break;
    }
  }

  if (assigneeInput && assigneeInput.value.trim().length > 40) {
    errors.push([assigneeInput, "assignee too long"]);
  }

  return errors;
}

function _showFormError(form, message) {
  let alert = form.querySelector(".alert.alert-danger");
  if (!alert) {
    alert = document.createElement("div");
    alert.className = "alert alert-danger";
    alert.setAttribute("role", "alert");
    form.prepend(alert);
  }
  alert.textContent = message;
}

function _resetDialog(form) {
  form.reset();
  for (const el of form.querySelectorAll(".is-invalid")) {
    _clearInvalid(el);
  }
  const alert = form.querySelector(".alert");
  if (alert) {
    alert.remove();
  }
}

function setUpNewTodoDialog() {
  const dialog = document.getElementById("new-todo-dialog");
  const open = document.querySelector('[data-action="new-todo"]');
  if (!dialog || !open) {
    return;
  }
  const form = dialog.querySelector("form");
  form.noValidate = true;

  open.addEventListener("click", () => dialog.showModal());
  dialog.querySelector('[data-action="cancel"]').addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => _resetDialog(form));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const existingAlert = form.querySelector(".alert");
    if (existingAlert) {
      existingAlert.remove();
    }

    const errors = _validateForm(form);
    if (errors.length > 0) {
      for (const [input, message] of errors) {
        _setInvalid(input, message);
      }
      errors[0][0].focus();
      return;
    }

    let response;
    try {
      response = await fetch("/add", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams(new FormData(form)),
        redirect: "manual",
      });
    } catch (error) {
      _showFormError(form, `Request failed: ${error.message}`);
      return;
    }

    if (response.type === "opaqueredirect" || response.ok) {
      window.location.reload();
      return;
    }

    const text = await response.text();
    _showFormError(form, text || `Error: HTTP ${response.status}`);
  });
}

function showError(message) {
  let alert = document.getElementById("board-error");
  if (!alert) {
    alert = document.createElement("div");
    alert.id = "board-error";
    alert.className = "alert alert-danger";
    alert.setAttribute("role", "alert");
    document.querySelector("main").before(alert);
  }
  alert.textContent = message;
}

async function moveItem(id, status) {
  let response;
  try {
    response = await fetch("/move", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ id, status }),
      redirect: "manual",
    });
  } catch (error) {
    showError(`Move failed: ${error.message}`);
    return;
  }
  // the 303 to / comes back as an opaque redirect (status 0) with redirect: "manual"
  if (response.type === "opaqueredirect" || response.ok) {
    window.location.reload();
    return;
  }
  showError((await response.text()) || `Move failed: HTTP ${response.status}`);
}

function setUpDragAndDrop() {
  let dragged = null;
  for (const item of document.querySelectorAll("article[data-id]")) {
    item.addEventListener("dragstart", (event) => {
      dragged = item;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", item.dataset.id);
    });
    item.addEventListener("dragend", () => {
      dragged = null;
    });
  }
  for (const column of document.querySelectorAll("section[data-status]")) {
    column.addEventListener("dragover", (event) => {
      if (!dragged) {
        return;
      }
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      column.classList.add("border-primary");
    });
    column.addEventListener("dragleave", (event) => {
      if (!column.contains(event.relatedTarget)) {
        column.classList.remove("border-primary");
      }
    });
    column.addEventListener("drop", (event) => {
      event.preventDefault();
      column.classList.remove("border-primary");
      const item = dragged;
      dragged = null;
      if (!item || column.contains(item)) {
        return; // its own column: nothing to send
      }
      moveItem(item.dataset.id, column.dataset.status);
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setUpNewTodoDialog();
  setUpDragAndDrop();
});
