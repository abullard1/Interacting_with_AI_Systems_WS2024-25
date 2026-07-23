

import "/styles/navbar.css";
import { bugReportModal } from "./BugReportModal.js";

class NavbarComponent extends HTMLElement {
  connectedCallback() {
    fetch("/navbar.html")
      .then((response) => response.text())
      .then((html) => {
        this.innerHTML = html;
        
        this.setupEventListeners();
      })
      .catch((err) => {
        console.error("Error loading navbar:", err);
      });
  }
  
  setupEventListeners() {
    const reportBugBtn = document.getElementById('reportBugBtn');
    if (reportBugBtn) {
      reportBugBtn.addEventListener('click', () => {
        bugReportModal.show();
      });
    }
  }
}

customElements.define("navbar-component", NavbarComponent);
