const state = {
  runtime: { status: "UNKNOWN", source: "not connected" },
  model: { status: "UNKNOWN", source: "not connected" },
  spine: { status: "UNKNOWN", source: "not connected" },
  history: { status: "UNKNOWN", source: "not connected" },
  sessionEvents: []
};

const esc = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const statusTag = (value) => {
  const cls = String(value).toLowerCase().replaceAll(/[^a-z_]/g, "");
  return `<span class="tag ${cls}">${esc(value)}</span>`;
};

function render() {
  const root = document.getElementById("app");
  const events = state.sessionEvents;

  root.innerHTML = `
    <main>
      <header class="panel hero">
        <div class="eyebrow">EVEZ OS / EVIDENCE RUNTIME</div>
        <h1>Operator Console</h1>
        <p class="muted">
          Observable runtime state only. No fabricated revenue, route scores,
          bottleneck percentages, causal edges, or persistence claims.
        </p>
        <div class="law">DECLARED ≠ EFFECTIVE · UNKNOWN stays UNKNOWN</div>
      </header>

      <section class="grid four">
        ${[
          ["Runtime", state.runtime],
          ["Model", state.model],
          ["Event Spine", state.spine],
          ["History", state.history],
        ].map(([label, item]) => `
          <article class="panel card">
            <div class="muted">${esc(label)}</div>
            <h2>${statusTag(item.status)}</h2>
            <div class="small">${esc(item.source)}</div>
          </article>
        `).join("")}
      </section>

      <section class="grid two">
        <article class="panel">
          <div class="section-head">
            <h2>Runtime Probe</h2>
            <button class="btn" id="probe">Probe localhost</button>
          </div>
          <p class="muted">
            The browser may attempt the actual local EVEZ endpoint at
            <code>127.0.0.1:8787</code>. A failed probe is recorded as
            UNKNOWN, not converted into a fake offline/online claim.
          </p>
          <pre id="probe-result">No probe performed.</pre>
        </article>

        <article class="panel">
          <h2>Epistemic State</h2>
          <div class="state-row"><span>Captured</span>${statusTag("PROPOSED")}</div>
          <div class="state-row"><span>Observed</span>${statusTag("UNKNOWN")}</div>
          <div class="state-row"><span>Verified</span>${statusTag("UNKNOWN")}</div>
          <div class="state-row"><span>Causal</span>${statusTag("NOT_ASSERTED")}</div>
          <div class="state-row"><span>Persistence</span>${statusTag("UNKNOWN")}</div>
        </article>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Mutation Intake</h2>
            <p class="muted">Creates a deterministic session artifact. It does not pretend to commit it to a remote system.</p>
          </div>
          <button class="btn" id="capture">Capture</button>
        </div>
        <div class="grid two">
          <input id="mutation" class="input" placeholder="mutation or objective">
          <input id="parent" class="input" placeholder="parent event hash (optional)">
        </div>
        <div class="spacer"></div>
        <textarea id="payload" placeholder='JSON payload, or plain text'></textarea>
        <div class="spacer"></div>
        <div id="capture-result" class="result">Nothing captured.</div>
      </section>

      <section class="panel">
        <div class="section-head">
          <h2>Session Witnesses</h2>
          <span class="muted">${events.length} captured</span>
        </div>
        ${events.length ? events.map((event, index) => `
          <div class="event">
            <div class="event-top">
              <strong>${index + 1}. ${esc(event.mutation)}</strong>
              ${statusTag(event.state)}
            </div>
            <div class="small">artifact: ${esc(event.hash)}</div>
            <div class="small">association: SESSION_ONLY / NOT_COMMITTED</div>
          </div>
        `).join("") : '<div class="muted">No session witnesses.</div>'}
      </section>
    </main>
  `;

  document.getElementById("probe").onclick = probe;
  document.getElementById("capture").onclick = capture;
}

async function digest(value) {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function probe() {
  const result = document.getElementById("probe-result");
  result.textContent = "Probing 127.0.0.1:8787…";

  try {
    const response = await fetch("http://127.0.0.1:8787/health", {
      cache: "no-store",
    });
    const data = await response.json();

    state.runtime = { status: data.ok ? "OBSERVED" : "UNKNOWN", source: "localhost /health" };
    state.model = {
      status: data.model_server ? "DECLARED" : "UNKNOWN",
      source: data.model_server || "not reported",
    };
    state.spine = {
      status: data.event_spine ? "AVAILABLE" : "UNKNOWN",
      source: "localhost /health",
    };

    result.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    state.runtime = { status: "UNKNOWN", source: "probe failed; no inference made" };
    result.textContent = "UNKNOWN\n" + String(error);
  }

  render();
}

async function capture() {
  const mutation = document.getElementById("mutation").value.trim();
  const parent = document.getElementById("parent").value.trim();
  const raw = document.getElementById("payload").value;

  if (!mutation) {
    document.getElementById("capture-result").textContent = "Mutation/objective is required.";
    return;
  }

  let payload = raw;
  try {
    payload = raw ? JSON.stringify(JSON.parse(raw)) : "";
  } catch {
    payload = raw;
  }

  const canonical = JSON.stringify({
    schema: "EVEZ/OPERATOR-CAPTURE/v1",
    mutation,
    parent: parent || null,
    payload,
    state: "PROPOSED",
  });

  const hash = await digest(canonical);

  state.sessionEvents.unshift({
    mutation,
    hash,
    state: "PROPOSED",
  });

  render();
  document.getElementById("capture-result").textContent =
    "CAPTURED / PROPOSED / SESSION_ONLY / NOT_COMMITTED\n" +
    "artifact: " + hash;
}

document.addEventListener("DOMContentLoaded", render);
