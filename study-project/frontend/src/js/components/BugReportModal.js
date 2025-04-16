/**
 * Bug Report Modal Web Component
 * Provides a modal dialog for reporting bugs with study token integration.
 */

import { Modal } from 'bootstrap';
import { setButtonLoading } from '../loading-button-change.js';
import Cookies from 'js-cookie';

class BugReportModal extends HTMLElement {
  constructor() {
    super();
    this.elements = {};
  }
  
  async connectedCallback() {
    try {
      const response = await fetch("/bug-report-modal.html");
      const html = await response.text();
      this.initializeModal(html);
    } catch (err) {
      console.error("Error loading bug report modal:", err);
    }
  }
  
  initializeModal(html) {
    const template = document.createElement('template');
    template.innerHTML = html.trim();
    this.elements.modal = template.content.querySelector('.modal');
    
    if (!this.elements.modal) {
      console.error("Could not find modal element in template");
      return;
    }
    
    document.body.appendChild(this.elements.modal);
    this.bootstrapModal = new Modal(this.elements.modal);
    
    this.cacheElements();
    
    this.setupEventListeners();
    
    this.resetForm();
  }
  
  cacheElements() {
    const selectors = {
      form: '#bugReportForm',
      description: '#bugReportDescription',
      type: '#bugReportType',
      page: '#bugReportPage',
      tokenCheck: '#includeTokenCheck',
      charCount: '#bugReportCharCount',
      submitBtn: '#bugReportSubmitBtn',
      cancelBtn: '.btn-secondary',
      successAlert: '#bugReportSuccess',
      errorAlert: '#bugReportError'
    };
    
    for (const [key, selector] of Object.entries(selectors)) {
      this.elements[key] = this.elements.modal.querySelector(selector);
    }
  }
  
  setupEventListeners() {
    this.elements.description.addEventListener('input', () => {
      const maxLength = parseInt(this.elements.description.getAttribute('maxlength'));
      this.elements.charCount.textContent = maxLength - this.elements.description.value.length;
    });
    
    this.elements.submitBtn.addEventListener('click', () => this.handleSubmit());
    
    this.elements.modal.addEventListener('hidden.bs.modal', () => this.resetForm());
  }
  
  async handleSubmit() {
    if (!this.validateForm()) return;
    
    setButtonLoading(true, false, 'bugReportSubmitBtn', 'Absenden');
    
    try {
      const reportData = this.collectFormData();
      await this.submitReport(reportData);
      this.showSuccess();
    } catch (error) {
      console.error("Error submitting bug report:", error);
      this.showError(error.message);
      setButtonLoading(false, true, 'bugReportSubmitBtn');
    }
  }
  
  /**
   * Validate form inputs
   */
  validateForm() {
    if (!this.elements.type.value) {
      alert("Bitte wähle die Art des Problems aus.");
      return false;
    }
    
    if (!this.elements.description.value.trim()) {
      alert("Bitte gib eine Beschreibung des Problems ein.");
      return false;
    }
    
    return true;
  }
  
  /**
   * Collect form data
   */
  collectFormData() {
    const studyToken = Cookies.get('study_token');
    
    return {
      type: this.elements.type.value,
      description: this.elements.description.value.trim(),
      page: this.elements.page.value,
      userAgent: navigator.userAgent,
      studyToken: studyToken && this.elements.tokenCheck.checked ? studyToken : "No token available"
    };
  }
  
  /**
   * Submit report to API
   */
  async submitReport(data) {
    const response = await fetch('/api/report-bug', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`API error (${response.status}): ${errorText}`);
    }
  }
  
  /**
   * Show success message
   */
  showSuccess() {
    this.elements.form.classList.add('d-none');
    this.elements.successAlert.classList.remove('d-none');
    this.elements.errorAlert.classList.add('d-none');
    this.elements.submitBtn.classList.add('d-none');
    this.elements.cancelBtn.textContent = 'Schließen';
    
    setTimeout(() => this.bootstrapModal.hide(), 3000);
  }
  
  /**
   * Show error message
   */
  showError(message) {
    this.elements.errorAlert.textContent = message || "Es ist ein Fehler aufgetreten. Bitte versuche es später erneut.";
    this.elements.errorAlert.classList.remove('d-none');
  }
  
  /**
   * Reset form to initial state
   */
  resetForm() {
    // Reset form and alerts
    this.elements.form.reset();
    this.elements.form.classList.remove('d-none');
    this.elements.successAlert.classList.add('d-none');
    this.elements.errorAlert.classList.add('d-none');
    
    // Reset character count
    const maxLength = parseInt(this.elements.description.getAttribute('maxlength') || 500);
    this.elements.charCount.textContent = maxLength;
    
    // Reset page field
    this.elements.page.value = window.location.pathname;
    
    // Reset buttons
    setButtonLoading(false, false, 'bugReportSubmitBtn', 'Absenden');
    this.elements.submitBtn.classList.remove('d-none');
    this.elements.cancelBtn.textContent = 'Abbrechen';
  }
  
  /**
   * Public methods to show/hide modal
   */
  show() {
    if (this.bootstrapModal) {
      this.resetForm();
      this.bootstrapModal.show();
    }
  }
  
  hide() {
    if (this.bootstrapModal) {
      this.bootstrapModal.hide();
    }
  }
}

// Register custom element
customElements.define('bug-report-modal', BugReportModal);

// Export singleton instance
export const bugReportModal = (() => {
  const existingModal = document.querySelector('bug-report-modal');
  return existingModal || document.body.appendChild(document.createElement('bug-report-modal'));
})(); 