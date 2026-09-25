// Minimal fetch-based glue between the server-rendered pages and the JSON API.
// No framework: forms POST, action buttons DELETE/POST, then reload.

async function submitJson(url, method, body) {
  const resp = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      detail = data.detail || JSON.stringify(data);
    } catch (_) { /* non-JSON error */ }
    alert(`Error ${resp.status}: ${detail}`);
    return null;
  }
  return resp;
}

// Add forms: collect named inputs, drop empty optionals, POST as JSON.
document.querySelectorAll("form.add-form").forEach((form) => {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const endpoint = form.dataset.endpoint;
    const body = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      const val = el.value.trim();
      if (val === "") continue;
      body[el.name] = el.type === "number" ? Number(val) : val;
    }
    const resp = await submitJson(endpoint, "POST", body);
    if (resp && form.dataset.reload) location.reload();
  });
});

// Delete buttons.
document.querySelectorAll("[data-delete]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    if (!confirm("Remove this item?")) return;
    const resp = await submitJson(btn.dataset.delete, "DELETE", null);
    if (resp) location.reload();
  });
});

// Acquire buttons (wishlist -> collection).
document.querySelectorAll("[data-acquire]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const resp = await submitJson(btn.dataset.acquire, "POST", null);
    if (resp) location.reload();
  });
});
