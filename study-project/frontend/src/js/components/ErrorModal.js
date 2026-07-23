import { Modal } from 'bootstrap';

class ErrorModalComponent extends HTMLElement {
  constructor() {
    super();
    this.modal = null;
    this.modalElement = null;
  }
  
  connectedCallback() {
    fetch("/error-modal.html")
      .then((response) => response.text())
      .then((html) => {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        
        const modalElement = template.content.querySelector('.modal');
        if (!modalElement) {
          console.error("Error: Could not find modal element in template");
          return;
        }
        
        this.modalElement = modalElement;
        
        document.body.appendChild(this.modalElement);
        
        this.modal = new Modal(this.modalElement);
      })
      .catch((err) => {
        console.error("Error loading error modal:", err);
      });
  }
  
  show(message, title = "Error") {
    if (this.modal) {
      document.getElementById('errorModalTitle').textContent = title;
      document.getElementById('errorModalBody').textContent = message;
      this.modal.show();
    } else {
      console.error("Error modal not initialized yet");
    }
  }
  
  hide() {
    if (this.modal) {
      this.modal.hide();
    }
  }
}

customElements.define('error-modal', ErrorModalComponent);

export const errorModal = (() => {
  const existingModal = document.querySelector('error-modal');
  if (existingModal) return existingModal;
  
  const modal = document.createElement('error-modal');
  document.body.appendChild(modal);
  return modal;
})(); 