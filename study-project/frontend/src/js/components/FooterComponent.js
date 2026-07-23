/**
 * Footer Web Component
 * Provides a consistent footer with progress tracking across all pages
 */

import "/styles/general.css";

class FooterComponent extends HTMLElement {
  static get observedAttributes() {
    return ["progress"];
  }

  connectedCallback() {
    fetch("/footer.html")
      .then((response) => response.text())
      .then((html) => {
        this.innerHTML = html;
        const progress = this.getAttribute("progress");
        if (progress) {
          this.updateProgress(progress);
        }
      })
      .catch((err) => {
        console.error("Error loading footer:", err);
      });
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "progress" && oldValue !== newValue) {
      this.updateProgress(newValue);
    }
  }

  updateProgress(value) {
    if (!this.isConnected) return;

    const progressBar = this.querySelector(".progress-bar");
    const progressText = this.querySelector(
      ".progress-element .text-muted span",
    );

    if (progressBar && progressText) {
      const progressValue = parseInt(value) || 0;
      progressBar.style.width = `${progressValue}%`;
      progressBar.setAttribute("aria-valuenow", progressValue);
      progressText.textContent = `${progressValue}% abgeschlossen`;
    }
  }
}

customElements.define("footer-component", FooterComponent);
