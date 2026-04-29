const form = document.querySelector("#modForm");
const cards = Array.from(document.querySelectorAll(".question-card"));
const scoreLabel = document.querySelector("#complexityScore");
const tierLabel = document.querySelector("#complexityTier");
const meter = document.querySelector("#complexityMeter");
const deadline = document.querySelector("#deadline");
const lookupInput = document.querySelector("#lookupInput");
const lookupButton = document.querySelector("#lookupButton");
const lookupResult = document.querySelector("#lookupResult");

function tierFor(score) {
  if (score >= 170) return "Campaign grade";
  if (score >= 120) return "Heavy build";
  if (score >= 75) return "Advanced";
  if (score >= 35) return "Standard";
  return "Recon";
}

function deadlinePoints() {
  const value = deadline?.value ?? "standard";
  if (value === "rush") return 28;
  if (value === "soon") return 12;
  return 0;
}

function calculateScore() {
  let score = deadlinePoints();
  let selectedCount = 0;

  cards.forEach((card) => {
    const checkbox = card.querySelector("input[type='checkbox']");
    const textarea = card.querySelector("textarea");
    const enabled = checkbox.checked;
    card.classList.toggle("active", enabled);

    if (!enabled) return;

    const base = Number(card.dataset.base);
    const risk = Number(card.dataset.risk);
    const words = textarea.value.trim().split(/\s+/).filter(Boolean).length;
    const detail = Math.min(18, Math.floor(words / 8));
    selectedCount += 1;
    score += base + risk + detail;
  });

  if (selectedCount >= 4) score += 16;
  if (selectedCount >= 6) score += 24;

  scoreLabel.textContent = `${score} pts`;
  tierLabel.textContent = tierFor(score);
  meter.value = Math.min(score, Number(meter.max));
}

function renderProgress(record, phases) {
  const phaseMarkup = phases
    .map((phase, index) => {
      const state = index < record.status_index ? "done" : index === record.status_index ? "current" : "";
      const label = index < record.status_index ? "Complete" : index === record.status_index ? "In progress" : "Queued";
      return `
        <div class="phase ${state}">
          <span class="phase-dot"></span>
          <div>
            <strong>${phase}</strong>
            <span>${label}</span>
          </div>
          <em>Step ${index + 1} / ${phases.length}</em>
        </div>
      `;
    })
    .join("");

  lookupResult.innerHTML = `
    <div class="progress-header">
      <div>
        <span class="label">Reference</span>
        <strong class="reference">${record.reference}</strong>
      </div>
      <div>
        <span class="label">Complexity</span>
        <strong>${record.score} pts · ${record.tier}</strong>
      </div>
    </div>
    <p><strong>${record.project_name}</strong> · ${record.notes}</p>
    <div class="phase-list">${phaseMarkup}</div>
  `;
}

async function lookupReference() {
  const reference = lookupInput.value.trim();
  if (!reference) {
    lookupResult.innerHTML = `<span class="empty-state">Enter a reference number first.</span>`;
    return;
  }

  lookupResult.innerHTML = `<span class="empty-state">Searching ${reference}...</span>`;
  const response = await fetch(`/api/requests/${encodeURIComponent(reference)}`);
  const payload = await response.json();

  if (!response.ok) {
    lookupResult.innerHTML = `<span class="empty-state">${payload.error}</span>`;
    return;
  }

  renderProgress(payload.record, payload.phases);
}

cards.forEach((card) => {
  card.addEventListener("input", calculateScore);
  card.addEventListener("change", calculateScore);
});

deadline?.addEventListener("change", calculateScore);
lookupButton?.addEventListener("click", lookupReference);
lookupInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") lookupReference();
});

form?.addEventListener("submit", (event) => {
  const selected = cards.some((card) => card.querySelector("input[type='checkbox']").checked);
  if (!selected) {
    event.preventDefault();
    scoreLabel.textContent = "Pick a module";
    tierLabel.textContent = "Select at least one build area";
  }
});

calculateScore();
