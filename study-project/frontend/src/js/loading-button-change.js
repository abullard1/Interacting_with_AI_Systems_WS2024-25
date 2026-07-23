export function setButtonLoading(isLoading, error = false, button_id, defaultText = "Fortfahren") {
  const button = document.getElementById(button_id);
  const spinner = button.querySelector(".spinner-border");
  const buttonText = button.querySelector(".button-text");

  button.disabled = isLoading || error;
  spinner.classList.toggle("d-none", !isLoading);
  if (error) {
    buttonText.textContent = "Fehler aufgetreten";
    button.classList.add("btn-danger");
  } else {
    buttonText.textContent = isLoading ? "Wird geladen..." : defaultText;
    button.classList.remove("btn-danger");
  }
}