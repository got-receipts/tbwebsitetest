const form = document.querySelector("#modForm");
const cards = Array.from(document.querySelectorAll(".question-card"));
const scoreLabel = document.querySelector("#complexityScore");
const tierLabel = document.querySelector("#complexityTier");
const meter = document.querySelector("#complexityMeter");
const timelineEstimate = document.querySelector("#timelineEstimate");
const deadline = document.querySelector("#deadline");
const lookupInput = document.querySelector("#lookupInput");
const lookupButton = document.querySelector("#lookupButton");
const lookupResult = document.querySelector("#lookupResult");
const modalButtons = Array.from(document.querySelectorAll("[data-modal]"));
const closeButtons = Array.from(document.querySelectorAll("[data-close-modal]"));
const roleSelect = document.querySelector("#roleSelect");
const accessCodeField = document.querySelector("#accessCodeField");
const workshopGrid = document.querySelector("#workshopDependencyGrid");
const workshopLoadMore = document.querySelector("#workshopLoadMore");
const workshopSearch = document.querySelector("#workshopSearch");
const workshopSearchButton = document.querySelector("#workshopSearchButton");
const workshopStatus = document.querySelector("#workshopStatus");
const pointBalanceNotice = document.querySelector("#pointBalanceNotice");
const submitButton = form?.querySelector("button[type='submit']");
const accountPointBalance = Number(form?.dataset.pointBalance || 0);
const steamLinked = form?.dataset.steamLinked !== "false";
let currentComplexityScore = 0;
const loadedWorkshopIds = new Set(
  Array.from(document.querySelectorAll(".dependency-check input[type='checkbox']")).map((input) =>
    input.name.replace(/^dep_/, "")
  )
);

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

function detailPoints(reason, isDependency = false) {
  const words = reason.split(/\s+/).filter(Boolean);
  const uniqueWords = new Set(words.map((word) => word.toLowerCase().replace(/[.,:;!?()[\]]/g, "")).filter(Boolean));
  const sentenceCount = Math.max(1, (reason.match(/[.!?\n]/g) || []).length);
  const score = isDependency
    ? words.length * 0.118 + uniqueWords.size * 0.037 + sentenceCount * 0.071
    : words.length * 0.173 + uniqueWords.size * 0.041 + sentenceCount * 0.119;
  return Math.min(isDependency ? 18 : 28, score);
}

function calculateScore() {
  if (!scoreLabel || !tierLabel || !meter) return;
  let score = deadlinePoints();
  let selectedCount = 0;
  let etaDays = 0;

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
    etaDays += Math.max(1, Math.round((base + risk + detail) / 12));
  });

  document.querySelectorAll(".option-check input:checked, .dependency-check input:checked").forEach((input) => {
    const parent = input.closest(".option-check, .dependency-check");
    const reason = parent?.querySelector(".reason-field")?.value.trim() || "";
    const isDependency = parent?.classList.contains("dependency-check");
    const reasonPoints = detailPoints(reason, isDependency);
    const basePoints = Number(input.dataset.points || 0);
    const itemScore = basePoints + reasonPoints;
    score += itemScore;
    etaDays += Math.max(1, Math.round(itemScore / (parent?.classList.contains("dependency-check") ? 16 : 12)));
    selectedCount += 1;
  });

  const dependencyCount = document.querySelectorAll(".dependency-check input:checked").length;

  if (selectedCount >= 4) score += 16;
  if (selectedCount >= 6) score += 24;
  if (dependencyCount >= 3) score += 12;
  if (dependencyCount >= 6) score += 18;
  currentComplexityScore = score;

  scoreLabel.textContent = `${score.toFixed(3)} pts`;
  tierLabel.textContent = tierFor(score);
  if (deadline?.value === "soon") etaDays += 2;
  if (deadline?.value === "rush") etaDays += 4;
  etaDays = Math.max(1, etaDays);
  if (timelineEstimate) {
    timelineEstimate.textContent =
      etaDays > 30
        ? `ETA: ${etaDays} days | auto review then freelance pool`
        : `ETA: ${etaDays} days`;
  }
  if (pointBalanceNotice) {
    if (!steamLinked) {
      pointBalanceNotice.textContent = "Steam link required before submission";
      pointBalanceNotice.classList.add("danger-text");
      meter.value = Math.min(score, Number(meter.max));
      return;
    }
    const remaining = accountPointBalance - score;
    if (remaining < 0) {
      pointBalanceNotice.textContent = `Need ${Math.abs(remaining).toFixed(3)} more account points`;
      pointBalanceNotice.classList.add("danger-text");
    } else {
      pointBalanceNotice.textContent = `Balance after submit: ${remaining.toFixed(3)} points`;
      pointBalanceNotice.classList.remove("danger-text");
    }
  }
  meter.value = Math.min(score, Number(meter.max));
}

function showCurationBlock(reasons) {
  const modal = document.querySelector("#curationBlockModal");
  const reasonList = document.querySelector("#curationBlockReasons");
  if (!modal || !reasonList) return;
  reasonList.innerHTML = reasons
    .map(
      (reason) => `
        <div class="curation-block-reason">
          <span aria-hidden="true">x</span>
          <div>
            <strong>${escapeHtml(reason.title)}</strong>
            <p>${escapeHtml(reason.detail)}</p>
          </div>
        </div>
      `
    )
    .join("");
  openModal("curationBlockModal");
}

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderWorkshopDependency(dependency) {
  const id = escapeHtml(dependency.id);
  const label = escapeHtml(dependency.label);
  const author = escapeHtml(dependency.author || "Workshop");
  const points = Number(dependency.points || 8);
  const rating = dependency.rating ? ` | ${Number(dependency.rating)}%` : "";
  return `
    <label class="dependency-check">
      <input name="dep_${id}" type="checkbox" data-points="${points}" />
      <input name="dep_${id}_label" type="hidden" value="${label}" />
      <input name="dep_${id}_author" type="hidden" value="${author}" />
      <input name="dep_${id}_points" type="hidden" value="${points}" />
      <input name="dep_${id}_workshop_id" type="hidden" value="${escapeHtml(dependency.workshop_id || "")}" />
      <input name="dep_${id}_source_url" type="hidden" value="${escapeHtml(dependency.source_url || "")}" />
      <span>
        <strong>${label}</strong>
        <em>by ${author} | ${points} pts${rating}</em>
      </span>
      <textarea
        class="reason-field"
        name="dep_${id}_reason"
        placeholder="Why is this dependency needed and how should it be used?"
      ></textarea>
    </label>
  `;
}

async function loadWorkshopPage({ page, query = "" }) {
  if (!workshopGrid || !workshopStatus) return;
  const params = new URLSearchParams();
  params.set("page", page || "1");
  if (query) params.set("q", query);
  workshopStatus.textContent = query ? "Searching workshop pages..." : `Loading workshop page ${page}...`;

  const response = await fetch(`/api/workshop?${params.toString()}`);
  const payload = await response.json();
  if (!response.ok) {
    workshopStatus.textContent = payload.error || "Workshop load failed";
    return;
  }

  let added = 0;
  payload.mods.forEach((dependency) => {
    if (!dependency.id || loadedWorkshopIds.has(dependency.id)) return;
    loadedWorkshopIds.add(dependency.id);
    workshopGrid.insertAdjacentHTML("beforeend", renderWorkshopDependency(dependency));
    added += 1;
  });

  if (workshopLoadMore && payload.next_page) {
    workshopLoadMore.dataset.nextPage = String(payload.next_page);
  }
  workshopStatus.textContent = `${loadedWorkshopIds.size} workshop mods loaded${added ? `, ${added} added` : ""}`;
  calculateScore();
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
        <strong>${record.score} pts | ${record.tier}</strong>
      </div>
    </div>
    <p><strong>${record.project_name}</strong> | ${record.notes}</p>
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

document.querySelectorAll(".option-check input, .dependency-check input").forEach((input) => {
  input.addEventListener("change", calculateScore);
});

document.querySelectorAll(".reason-field").forEach((field) => {
  field.addEventListener("input", calculateScore);
});

workshopGrid?.addEventListener("change", (event) => {
  if (event.target.matches("input[type='checkbox']")) calculateScore();
});

workshopGrid?.addEventListener("input", (event) => {
  if (event.target.matches(".reason-field")) calculateScore();
});

workshopLoadMore?.addEventListener("click", () => {
  loadWorkshopPage({ page: workshopLoadMore.dataset.nextPage || "5" });
});

workshopSearchButton?.addEventListener("click", () => {
  loadWorkshopPage({ page: 1, query: workshopSearch?.value.trim() || "" });
});

workshopSearch?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadWorkshopPage({ page: 1, query: workshopSearch.value.trim() });
  }
});

deadline?.addEventListener("change", calculateScore);
lookupButton?.addEventListener("click", lookupReference);
lookupInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") lookupReference();
});

form?.addEventListener("submit", (event) => {
  const selected =
    cards.some((card) => card.querySelector("input[type='checkbox']").checked) ||
    document.querySelectorAll(".option-check input:checked, .dependency-check input:checked").length > 0;
  const blockers = [];
  if (!selected) {
    event.preventDefault();
    scoreLabel.textContent = "Pick a module";
    tierLabel.textContent = "Select at least one build area";
    blockers.push({
      title: "No build scope selected",
      detail: "Choose at least one build system or workshop dependency before curation.",
    });
  }
  if (!steamLinked) {
    blockers.push({
      title: "Steam not connected",
      detail: "Link Steam so Arma Reforger gameplay points can be verified.",
    });
  }
  if (accountPointBalance <= 0 || accountPointBalance < currentComplexityScore) {
    const shortage = Math.max(currentComplexityScore - accountPointBalance, 0).toFixed(3);
    blockers.push({
      title: "Point balance is too low for project curation",
      detail:
        accountPointBalance <= 0
          ? "Your point bank has no spendable points yet."
          : `This build needs ${shortage} more points before it can proceed.`,
    });
  }
  if (blockers.length) {
    event.preventDefault();
    showCurationBlock(blockers);
  }
});

calculateScore();

function openModal(id, trigger) {
  const modal = document.querySelector(`#${id}`);
  if (!modal) return;
  const phase = trigger?.dataset.phase;
  const phaseTitle = document.querySelector("#phaseModalTitle");
  if (phase && phaseTitle) phaseTitle.textContent = phase;
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal(modal) {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

modalButtons.forEach((button) => {
  button.addEventListener("click", () => openModal(button.dataset.modal, button));
});

closeButtons.forEach((button) => {
  button.addEventListener("click", () => closeModal(button.closest(".modal-backdrop")));
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  document.querySelectorAll(".modal-backdrop.open").forEach(closeModal);
});

document.querySelectorAll(".modal-backdrop").forEach((modal) => {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal(modal);
  });
});

function syncAccessCodeField() {
  if (!roleSelect || !accessCodeField) return;
  accessCodeField.classList.toggle("muted-field", roleSelect.value === "customer");
}

roleSelect?.addEventListener("change", syncAccessCodeField);
syncAccessCodeField();
