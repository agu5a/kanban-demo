// Board behaviour, loaded with `defer` from the page; no library, no inline script.
// - New todo dialog: "New todo" opens it, Cancel and Escape (native <dialog>) close it without a request.
// - Drag and drop: an item dropped on another column is moved with POST /move, then the page reloads to show the
//   server's state; on an error the item stays and the server's text is shown in an alert above the columns.

function setUpNewTodoDialog() {
  const dialog = document.getElementById("new-todo-dialog");
  const open = document.querySelector('[data-action="new-todo"]');
  if (!dialog || !open) {
    return;
  }
  const form = dialog.querySelector("form");
  open.addEventListener("click", () => dialog.showModal());
  dialog.querySelector('[data-action="cancel"]').addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => form.reset());
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
