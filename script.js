const checkinForm = document.querySelector("#checkin-form");
const formMessage = document.querySelector("#form-message");

checkinForm.addEventListener("submit", (event) => {
  event.preventDefault();

  if (!checkinForm.reportValidity()) {
    return;
  }

  const formData = new FormData(checkinForm);
  const sleep = formData.get("sleep");
  const mood = formData.get("mood");
  const symptomNote = formData.get("symptoms").trim();
  const symptomText = symptomNote ? " Your symptom note is included." : "";

  formMessage.textContent =
    `Demo check-in complete: ${sleep} hours of sleep and ${mood.toLowerCase()} mood recorded on this page.${symptomText} Nothing was sent or saved.`;
});
