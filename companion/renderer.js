const form = document.querySelector("#presenceForm");
const stopButton = document.querySelector("#stopButton");
const siteButton = document.querySelector("#siteButton");
const loginButton = document.querySelector("#loginButton");
const statusLabel = document.querySelector("#status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    reference: document.querySelector("#reference").value.trim(),
    phase: document.querySelector("#phase").value,
    progress: document.querySelector("#progress").value.trim() || "Tracking project",
  };

  try {
    const result = await window.thunderCompanion.startPresence(payload);
    const presence = result.presence || payload;
    statusLabel.textContent = `Connected to website: ${presence.reference || "dashboard"} | ${presence.phase || "tracking"}`;
  } catch (error) {
    statusLabel.textContent = `Could not start Rich Presence: ${error.message}`;
  }
});

stopButton.addEventListener("click", async () => {
  await window.thunderCompanion.stopPresence();
  statusLabel.textContent = "Rich Presence stopped.";
});

siteButton.addEventListener("click", () => {
  window.thunderCompanion.openSite();
});

loginButton.addEventListener("click", () => {
  window.thunderCompanion.loginSite();
});
