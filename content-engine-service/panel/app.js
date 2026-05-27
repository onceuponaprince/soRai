const apiBaseEl = document.getElementById("apiBase");
const apiKeyEl = document.getElementById("apiKey");

function headers(extra = {}) {
  const h = { "Content-Type": "application/json", ...extra };
  const key = apiKeyEl.value.trim();
  if (key) h["x-api-key"] = key;
  return h;
}

async function request(path, opts = {}) {
  const base = apiBaseEl.value.trim().replace(/\/$/, "");
  const response = await fetch(`${base}${path}`, opts);
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = { error: "non-json response" };
  }
  return { ok: response.ok, status: response.status, payload };
}

function setPre(id, value) {
  document.getElementById(id).textContent = JSON.stringify(value, null, 2);
}

function roleListCsv(value) {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

document.getElementById("healthBtn").addEventListener("click", async () => {
  const out = await request("/health", { method: "GET" });
  setPre("healthOut", out);
});

document.getElementById("whoamiBtn").addEventListener("click", async () => {
  const out = await request("/api/v1/whoami", { method: "GET", headers: headers() });
  setPre("whoamiOut", out);
});

document.getElementById("profilesBtn").addEventListener("click", async () => {
  const out = await request("/api/v1/profiles", { method: "GET", headers: headers() });
  setPre("profilesOut", out);
});

document.getElementById("signupForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = {
    email: String(form.get("email") || "").trim(),
    requested_roles: roleListCsv(String(form.get("roles") || "operator")),
  };
  const out = await request("/api/v1/signup", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  setPre("signupOut", out);
});

document.getElementById("runForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = {
    profile: String(form.get("profile") || "general"),
    mode: String(form.get("mode") || "dry-run"),
    brief: String(form.get("brief") || ""),
  };
  const out = await request("/api/v1/runs", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  setPre("runOut", out);
});

async function loadPending() {
  const out = await request("/api/v1/signup/pending", { method: "GET", headers: headers() });
  const mount = document.getElementById("pendingList");
  mount.innerHTML = "";

  if (!out.ok) {
    mount.textContent = `${out.status}: ${JSON.stringify(out.payload)}`;
    return;
  }

  for (const item of out.payload.pending || []) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div>
        <strong>${item.email}</strong><br />
        <small>id=${item.id} roles=${(item.requested_roles || []).join(",")}</small>
      </div>
      <div class="actions">
        <button data-action="approve" data-id="${item.id}">Approve</button>
        <button data-action="reject" data-id="${item.id}">Reject</button>
      </div>
    `;
    mount.appendChild(row);
  }

  mount.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      const action = btn.getAttribute("data-action");
      await request(`/api/v1/signup/${id}/${action}`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ note: `${action}d in panel scaffold` }),
      });
      await loadPending();
    });
  });
}

document.getElementById("pendingBtn").addEventListener("click", loadPending);

async function loadApprovals() {
  const out = await request("/api/v1/approvals", { method: "GET", headers: headers() });
  const mount = document.getElementById("approvalsList");
  mount.innerHTML = "";

  if (!out.ok) {
    mount.textContent = `${out.status}: ${JSON.stringify(out.payload)}`;
    return;
  }

  for (const item of out.payload.approvals || []) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div>
        <strong>${item.event_id}</strong><br />
        <small>status=${item.approval_status} inbox=${item.inbox}</small>
      </div>
      <div class="actions">
        <button data-action="approve" data-id="${item.event_id}">Approve</button>
        <button data-action="reject" data-id="${item.event_id}">Reject</button>
      </div>
    `;
    mount.appendChild(row);
  }

  mount.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      const action = btn.getAttribute("data-action");
      await request(`/api/v1/approvals/${id}/${action}`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ note: `${action}d in panel scaffold` }),
      });
      await loadApprovals();
    });
  });
}

document.getElementById("approvalsBtn").addEventListener("click", loadApprovals);

async function loadKeys() {
  const out = await request("/api/v1/admin/api-keys", { method: "GET", headers: headers() });
  const mount = document.getElementById("keysList");
  mount.innerHTML = "";

  if (!out.ok) {
    mount.textContent = `${out.status}: ${JSON.stringify(out.payload)}`;
    return;
  }

  for (const key of out.payload.api_keys || []) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div>
        <strong>${key.email}</strong><br />
        <small>key=${key.api_key} roles=${(key.roles || []).join(",")} active=${key.is_active}</small>
      </div>
      <div class="actions">
        <button data-action="revoke" data-id="${key.api_key}">Revoke</button>
        <button data-action="reactivate" data-id="${key.api_key}">Reactivate</button>
      </div>
    `;
    mount.appendChild(row);
  }

  mount.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      const action = btn.getAttribute("data-action");
      await request(`/api/v1/admin/api-keys/${id}/${action}`, {
        method: "POST",
        headers: headers(),
      });
      await loadKeys();
    });
  });
}

document.getElementById("keysBtn").addEventListener("click", loadKeys);
