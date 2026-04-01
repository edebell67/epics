import {
  buildInitialFlowState,
  deferSelectedCandidate,
  dispatchIntent,
  parseVoiceIntent,
  selectCandidate,
  undoLastAction
} from "./state.js";

const app = document.querySelector("[data-app]");
const params = new URLSearchParams(window.location.search);

async function loadPayload() {
  const response = await fetch("./data/evidence-match-demo.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Unable to load demo payload (${response.status})`);
  }
  return response.json();
}

function currency(value) {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP"
  }).format(Number(value || 0));
}

function renderChip(reason) {
  return `<span class="reason-chip">${reason}</span>`;
}

function renderCandidate(candidate, selectedRank) {
  const selectedClass = candidate.candidate_rank === selectedRank ? "candidate candidate--selected" : "candidate";
  const leadCopy = candidate.candidate_rank === 1 ? "Best match" : `Choice ${candidate.candidate_rank}`;
  return `
    <button class="${selectedClass}" data-testid="candidate-card-${candidate.candidate_rank}" data-rank="${candidate.candidate_rank}" type="button">
      <div class="candidate__meta">
        <span class="candidate__lead">${leadCopy}</span>
        <span class="candidate__score">${Math.round(candidate.link_confidence * 100)}% confidence</span>
      </div>
      <div class="candidate__row">
        <strong>${candidate.merchant}</strong>
        <strong>${currency(candidate.amount)}</strong>
      </div>
      <div class="candidate__row candidate__row--muted">
        <span>${candidate.date}</span>
        <span>${candidate.bank_txn_id}</span>
      </div>
      <div class="candidate__chips">
        ${candidate.reasons.map(renderChip).join("")}
      </div>
    </button>
  `;
}

function renderIntentButton(label, intentName, parsedValue) {
  return `
    <button
      class="intent-button"
      type="button"
      data-intent-name="${intentName}"
      data-intent-value="${String(parsedValue)}"
    >
      ${label}
    </button>
  `;
}

function render(state, payload) {
  const contexts = payload.contexts || [];
  const selectedContext = contexts.find((context) => context.id === state.selectedContext) || contexts[0];
  const resolution = state.resolution;
  const summaryClass = resolution ? `summary summary--${resolution.type}` : "summary";
  const classification = state.classification;
  const chip = state.confirmationChip;
  const voiceExamples = payload.voiceCommandExamples || [];
  const transaction = state.transaction || {};

  app.innerHTML = `
    <div class="screen-shell">
      <div class="screen-shell__glow"></div>
      <main class="phone">
        ${chip ? `
          <section class="confirmation-chip" data-testid="confirmation-chip">
            <div>
              <p class="section-label">Applied ${chip.source === "voice" ? "by voice" : "by tap"}</p>
              <strong>${chip.summary}</strong>
            </div>
            <button class="confirmation-chip__undo" type="button" data-action="undo-last">Undo</button>
          </section>
        ` : ""}

        <section class="hero">
          <div class="hero__eyebrow">Voice triage</div>
          <h1>Speak or tap once. Confirm what changed. Undo in one tap.</h1>
          <p>${payload.heroCopy}</p>
        </section>

        <nav class="context-switch" aria-label="Workflow context">
          ${contexts.map((context) => `
            <button
              class="${context.id === state.selectedContext ? "context-switch__item context-switch__item--active" : "context-switch__item"}"
              type="button"
              data-context="${context.id}"
            >
              <span>${context.label}</span>
              <small>${context.summary}</small>
            </button>
          `).join("")}
        </nav>

        <section class="voice-panel">
          <div class="voice-panel__header">
            <div>
              <p class="section-label">Voice command</p>
              <h2>Try the MVP intent set</h2>
            </div>
            <span class="voice-badge">Text parser demo</span>
          </div>
          <form class="voice-form" data-voice-form>
            <label class="sr-only" for="voice-command">Voice command</label>
            <input id="voice-command" name="voice-command" type="text" placeholder="Category: Travel" value="${params.get("voice") || ""}" data-testid="voice-command-input">
            <button type="submit" class="primary-action" data-testid="voice-apply-action">Apply</button>
          </form>
          <div class="voice-examples">
            ${voiceExamples.map((example) => `<button type="button" class="voice-example" data-voice-example="${example}">${example}</button>`).join("")}
          </div>
        </section>

        <section class="triage-panel">
          <div>
            <p class="section-label">Inbox micro-decision</p>
            <h2>${transaction.merchant}</h2>
            <p>${selectedContext.description}</p>
          </div>
          <dl class="triage-panel__meta">
            <div>
              <dt>Date</dt>
              <dd>${transaction.date}</dd>
            </div>
            <div>
              <dt>Amount</dt>
              <dd>${currency(transaction.amount)}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>${classification.category_name || "Unassigned"}</dd>
            </div>
            <div>
              <dt>Business or personal</dt>
              <dd>${classification.business_personal || "Missing"}</dd>
            </div>
            <div>
              <dt>Split</dt>
              <dd>${classification.is_split ? `${classification.split_business_pct}% business` : "Not split"}</dd>
            </div>
          </dl>
          <div class="intent-grid">
            ${renderIntentButton("Category: Travel", "category", "Travel")}
            ${renderIntentButton("Business", "business_personal", "BUSINESS")}
            ${renderIntentButton("Personal", "business_personal", "PERSONAL")}
            ${renderIntentButton("Split 40%", "split", "40")}
            ${renderIntentButton("Attach receipt", "attach_receipt", "true")}
            ${renderIntentButton("No match", "no_match", "true")}
          </div>
        </section>

        <section class="receipt-panel">
          <div>
            <p class="section-label">Receipt capture</p>
            <h2>${state.evidence.fileName}</h2>
            <p>${payload.attachHint}</p>
          </div>
          <div class="receipt-preview">
            <div class="receipt-preview__thumb"></div>
            <dl>
              <div>
                <dt>Merchant</dt>
                <dd>${state.evidence.merchant}</dd>
              </div>
              <div>
                <dt>Date</dt>
                <dd>${state.evidence.doc_date}</dd>
              </div>
              <div>
                <dt>Amount</dt>
                <dd>${currency(state.evidence.amount)}</dd>
              </div>
            </dl>
          </div>
          <div class="receipt-actions">
            <button class="primary-action" data-intent-name="attach_receipt" data-intent-value="true" type="button">
              ${state.receiptAttached ? "Review top matches" : "Attach receipt"}
            </button>
            <span class="receipt-actions__hint">${payload.pendingCopy}</span>
          </div>
        </section>

        <section class="${summaryClass}" data-testid="resolution-summary">
          <p class="section-label">Current status</p>
          ${
            resolution
              ? `
                <h3>${resolution.title}</h3>
                <p>${resolution.detail}</p>
                <strong>${resolution.createsExportBlocker ? "Export blocker created" : state.blockerStatus.safeCopy}</strong>
              `
              : `
                <h3>No receipt decision made yet</h3>
                <p>${payload.sheetCopy}</p>
                <strong>${state.blockerStatus.safeCopy}</strong>
              `
          }
        </section>

        <section class="activity-panel">
          <p class="section-label">Why this works</p>
          <ul>
            ${payload.outcomes.map((item) => `<li>${item}</li>`).join("")}
          </ul>
        </section>
      </main>

      ${
        state.sheetOpen
          ? `
            <aside class="sheet-backdrop" data-testid="candidate-sheet">
              <div class="sheet">
                <div class="sheet__handle"></div>
                <div class="sheet__header">
                  <div>
                    <p class="section-label">Top 3 candidates</p>
                    <h2>Confirm the best bank match</h2>
                  </div>
                  <button class="sheet__close" type="button" data-action="close-sheet" aria-label="Close">&times;</button>
                </div>
                <p class="sheet__copy">${payload.sheetCopy}</p>
                <div class="candidate-list">
                  ${state.candidates.map((candidate) => renderCandidate(candidate, state.selectedRank)).join("")}
                </div>
                <div class="sheet__footer">
                  <button class="confirm-action" type="button" data-intent-name="match_rank" data-intent-value="${state.selectedRank}" data-testid="confirm-action">Confirm match</button>
                  <button class="secondary-action" type="button" data-intent-name="no_match" data-intent-value="true" data-testid="no-match-action">No match</button>
                  <button class="ghost-action" type="button" data-testid="later-action">Later</button>
                </div>
              </div>
            </aside>
          `
          : ""
      }
    </div>
  `;

  function applyIntentAndRender(intent) {
    dispatchIntent(state, intent);
    render(state, payload);
  }

  for (const button of app.querySelectorAll("[data-context]")) {
    button.addEventListener("click", () => {
      state.selectedContext = button.dataset.context;
      render(state, payload);
    });
  }

  for (const button of app.querySelectorAll("[data-intent-name]")) {
    button.addEventListener("click", () => {
      const { intentName, intentValue } = button.dataset;
      const parsedValue = intentName === "split" || intentName === "match_rank"
        ? Number(intentValue)
        : intentName === "attach_receipt" || intentName === "no_match"
          ? true
          : intentValue;
      applyIntentAndRender({
        intentName,
        parsedValue,
        source: "tap",
        raw: button.textContent.trim()
      });
    });
  }

  const voiceForm = app.querySelector("[data-voice-form]");
  if (voiceForm) {
    voiceForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = app.querySelector("[data-testid='voice-command-input']");
      const intent = parseVoiceIntent(input.value, state);
      if (!intent) {
        input.setCustomValidity("Command not recognised");
        input.reportValidity();
        return;
      }
      input.setCustomValidity("");
      applyIntentAndRender(intent);
    });
  }

  for (const button of app.querySelectorAll("[data-voice-example]")) {
    button.addEventListener("click", () => {
      const command = button.dataset.voiceExample;
      const input = app.querySelector("[data-testid='voice-command-input']");
      input.value = command;
      const intent = parseVoiceIntent(command, state);
      if (intent) {
        applyIntentAndRender(intent);
      }
    });
  }

  const closeButton = app.querySelector("[data-action='close-sheet']");
  if (closeButton) {
    closeButton.addEventListener("click", () => {
      state.sheetOpen = false;
      render(state, payload);
    });
  }

  const undoButton = app.querySelector("[data-action='undo-last']");
  if (undoButton) {
    undoButton.addEventListener("click", () => {
      undoLastAction(state);
      render(state, payload);
    });
  }

  for (const button of app.querySelectorAll("[data-rank]")) {
    button.addEventListener("click", () => {
      selectCandidate(state, Number(button.dataset.rank));
      render(state, payload);
    });
  }

  const laterButton = app.querySelector("[data-testid='later-action']");
  if (laterButton) {
    laterButton.addEventListener("click", () => {
      deferSelectedCandidate(state);
      render(state, payload);
    });
  }
}

async function start() {
  try {
    const payload = await loadPayload();
    const state = buildInitialFlowState(payload, {
      context: params.get("context") || payload.defaultContext,
      selectedRank: params.get("rank")
    });

    if (params.get("sheet") === "open") {
      dispatchIntent(state, {
        intentName: "attach_receipt",
        parsedValue: true,
        source: "tap",
        raw: "Attach receipt"
      });
    }

    const bootVoiceCommand = params.get("voice");
    if (bootVoiceCommand) {
      const intent = parseVoiceIntent(bootVoiceCommand, state);
      if (intent) {
        dispatchIntent(state, intent);
      }
    }

    render(state, payload);
  } catch (error) {
    app.innerHTML = `
      <section class="error-state">
        <h1>Voice demo failed</h1>
        <p>${error.message}</p>
      </section>
    `;
    console.error(error);
  }
}

start();
