// New todo dialog: "New todo" opens it, Cancel and Escape (native <dialog>) close it without a request.
document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.getElementById("new-todo-dialog");
  const open = document.querySelector('[data-action="new-todo"]');
  if (!dialog || !open) {
    return;
  }
  const form = dialog.querySelector("form");
  open.addEventListener("click", () => dialog.showModal());
  dialog.querySelector('[data-action="cancel"]').addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => form.reset());
});
