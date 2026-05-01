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
const donationForm = document.querySelector("#donationForm");
const charitySearchInput = document.querySelector("#charitySearch");
const charityCauseFilter = document.querySelector("#charityCauseFilter");
const charitySelect = document.querySelector("#charitySelect");
const charityFilterStatus = document.querySelector("#charityFilterStatus");
const donationPointsInput = document.querySelector("#donationPoints");
const donationValuePreview = document.querySelector("#donationValuePreview");
const donationBalancePreview = document.querySelector("#donationBalancePreview");
const publicCharityRows = Array.from(document.querySelectorAll("#publicCharityList .client-request-row"));
const platformSelect = document.querySelector("#platformSelect");
const consolePlatformFields = document.querySelector("#consolePlatformFields");
const submitButton = form?.querySelector("button[type='submit']");
const accountPointBalance = Number(form?.dataset.pointBalance || 0);
const gameAccountLinked = form?.dataset.steamLinked !== "false";
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
    if (!gameAccountLinked) {
      pointBalanceNotice.textContent = "Steam link or console verification required";
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

function formatCurrency(value) {
  return Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function syncDonationPreview() {
  if (!donationForm || !donationPointsInput || !donationValuePreview || !donationBalancePreview) return;
  const rate = Number(donationForm.dataset.pointCashRate || 0);
  const pointBalance = Number(donationForm.dataset.pointBalance || 0);
  const points = Number(donationPointsInput.value || 0);
  const estimatedValue = points * rate;
  const remainingPoints = pointBalance - points;

  if (points > 0) {
    donationValuePreview.textContent = `${points.toFixed(3)} points is about $${formatCurrency(estimatedValue)}.`;
    if (remainingPoints < 0) {
      donationBalancePreview.textContent = `This donation exceeds your bank by ${Math.abs(remainingPoints).toFixed(3)} points.`;
      donationBalancePreview.classList.add("danger-text");
    } else {
      donationBalancePreview.textContent = `Remaining bank after donation: ${remainingPoints.toFixed(3)} points, about $${formatCurrency(remainingPoints * rate)}.`;
      donationBalancePreview.classList.remove("danger-text");
    }
    return;
  }

  donationValuePreview.textContent = "Enter points to preview the donation amount.";
  donationBalancePreview.textContent = `Remaining bank after donation: $${formatCurrency(pointBalance * rate)} in value.`;
  donationBalancePreview.classList.remove("danger-text");
}

function syncVisibleCharityOption() {
  if (!charitySelect) return;
  const selectedOption = charitySelect.selectedOptions[0];
  if (selectedOption && !selectedOption.hidden) return;
  const firstVisible = Array.from(charitySelect.options).find((option) => !option.hidden);
  if (firstVisible) charitySelect.value = firstVisible.value;
}

function filterCharityList() {
  if (!charitySelect || !charityFilterStatus) return;
  const searchValue = (charitySearchInput?.value || "").trim().toLowerCase();
  const causeValue = (charityCauseFilter?.value || "").trim().toLowerCase();
  let visibleCount = 0;

  Array.from(charitySelect.options).forEach((option) => {
    if (option.value === "custom") {
      option.hidden = false;
      return;
    }
    const name = option.dataset.charityName || "";
    const cause = option.dataset.charityCause || "";
    const matchesSearch = !searchValue || name.includes(searchValue) || cause.includes(searchValue);
    const matchesCause = !causeValue || cause === causeValue;
    option.hidden = !(matchesSearch && matchesCause);
    if (!option.hidden) visibleCount += 1;
  });

  publicCharityRows.forEach((row) => {
    const name = row.dataset.charityName || "";
    const cause = row.dataset.charityCause || "";
    const matchesSearch = !searchValue || name.includes(searchValue) || cause.includes(searchValue);
    const matchesCause = !causeValue || cause === causeValue;
    row.hidden = !(matchesSearch && matchesCause);
  });

  charityFilterStatus.textContent = visibleCount
    ? `${visibleCount} nonprofits match the current filters.`
    : "No nonprofits match the current filters. Use Custom GoFundMe nonprofit if needed.";
  syncVisibleCharityOption();
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

donationPointsInput?.addEventListener("input", syncDonationPreview);
charitySearchInput?.addEventListener("input", filterCharityList);
charityCauseFilter?.addEventListener("change", filterCharityList);

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
  if (!gameAccountLinked) {
    blockers.push({
      title: "Platform account not verified",
      detail: "Link Steam or submit approved Xbox/PlayStation verification before project curation.",
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
  if (!modal) return;
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

modalButtons.forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    const currentModal = button.closest(".modal-backdrop.open");
    if (currentModal) closeModal(currentModal);
    openModal(button.dataset.modal, button);
  });
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
syncDonationPreview();
filterCharityList();

function syncPlatformFields() {
  if (!platformSelect || !consolePlatformFields) return;
  consolePlatformFields.classList.toggle("muted-field", platformSelect.value === "steam");
}

platformSelect?.addEventListener("change", syncPlatformFields);
syncPlatformFields();

function launchConfetti(modal) {
  const stage = modal?.querySelector(".confetti-stage");
  if (!stage) return;
  stage.innerHTML = "";
  const colors = ["#f6c65b", "#47d5c3", "#f5f7f7", "#ff9f9f", "#8fb7ff"];
  for (let index = 0; index < 52; index += 1) {
    const piece = document.createElement("span");
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.setProperty("--confetti-color", colors[index % colors.length]);
    piece.style.setProperty("--confetti-delay", `${Math.random() * 0.45}s`);
    piece.style.setProperty("--confetti-drift", `${Math.random() * 120 - 60}px`);
    piece.style.setProperty("--confetti-rotate", `${Math.random() * 720 - 360}deg`);
    stage.appendChild(piece);
  }
}

document.querySelectorAll("[data-auto-confetti='true']").forEach((modal) => {
  launchConfetti(modal);
  setTimeout(() => launchConfetti(modal), 850);
});
