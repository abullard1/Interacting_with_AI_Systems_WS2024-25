/**
 * Already Completed Page Controller
 */

import { auth, db } from "./firebase-services.js";
import { 
  doc, 
  updateDoc,
  serverTimestamp,
  getDoc
} from "firebase/firestore";
import { onAuthStateChanged } from "firebase/auth";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';
import Cookies from "js-cookie";

console.log("[Already Completed] already-completed.js loaded.");

// Check on page load that the study is actually completed
document.addEventListener("DOMContentLoaded", () => {
  // Verify the study is truly completed via cookie
  const studyCompleted = Cookies.get("study-completed") === "true";
  
  // If not completed, redirect to homepage
  if (!studyCompleted) {
    console.warn("[Already Completed] Study not actually completed, redirecting to homepage");
    window.location.href = "/";
    return;
  }
  
  // Continue with the rest of the initialization
  console.log("[Already Completed] DOM fully loaded and parsed");

  // Get DOM elements
  const matrikelnummerInput = document.getElementById("matrikelnummer");
  const submitButton = document.getElementById("submit-btn");
  const successMessage = document.getElementById("success-message");
  const matrikelnummerForm = document.getElementById("matrikelnummer-form");
  const loadingSpinner = document.getElementById("loading-spinner");
  
  
  // Function to show the form and hide the spinner
  function showMatrikelnummerForm() {
    console.log("[Already Completed] Showing Matrikelnummer form");
    loadingSpinner.classList.add("d-none");
    matrikelnummerForm.classList.remove("d-none");
  }
  
  // Check if user already has a Matrikelnummer saved
  async function checkExistingMatrikelnummer(user) {
    console.log("[Already Completed] Checking for existing Matrikelnummer for user:", user);
    
    try {
      if (!user) {
        console.error("[Already Completed] Error: No authenticated user found when checking existing Matrikelnummer");
        showMatrikelnummerForm(); 
        return;
      }
      
      // Get user document reference
      const userDocRef = doc(db, "users", user.displayName);
      console.log("[Already Completed] User document reference:", userDocRef);
      
      // Get user document
      const userDoc = await getDoc(userDocRef);
      console.log("[Already Completed] User document exists:", userDoc.exists());
      
      if (userDoc.exists()) {
        const userData = userDoc.data();
        console.log("[Already Completed] User data:", userData);
        
        // Check if studyCompensation and matrikelnummer exist
        if (userData.studyCompensation && userData.studyCompensation.matrikelnummer) {
          console.log("[Already Completed] Existing Matrikelnummer found:", userData.studyCompensation.matrikelnummer);
          
          // Update the UI to reflect existing entry
          const matrikelnummerText = matrikelnummerForm.querySelector("p.text-center");
          matrikelnummerText.textContent = "Du hast bereits eine Matrikelnummer eingetragen. Du kannst sie hier aktualisieren, falls nötig:";
          
          // Set the input value to the existing Matrikelnummer
          matrikelnummerInput.value = userData.studyCompensation.matrikelnummer;
          
          // Update button text
          submitButton.querySelector(".button-text").textContent = "Matr. aktualisieren";
          
          console.log("[Already Completed] UI updated for existing Matrikelnummer");
        } else {
          console.log("[Already Completed] No existing Matrikelnummer found in user data");
        }
      } else {
        console.log("[Already Completed] User document does not exist");
      }
      
      // Show the form after checking, regardless of the result
      showMatrikelnummerForm();
      
    } catch (error) {
      console.error("[Already Completed] Error checking for existing Matrikelnummer:", error);
      
      showMatrikelnummerForm();
    }
  }
  
  // Listen for authentication state changes
  let authCheckTimeout = setTimeout(() => {
    console.log("[Already Completed] Auth check timeout reached, showing form");
    showMatrikelnummerForm(); 
  }, 5000); 
  
  onAuthStateChanged(auth, (user) => {
    console.log("[Already Completed] Auth state changed, user:", user);
    clearTimeout(authCheckTimeout); 
    
    if (user) {
      // User is signed in, call the function to check for existing Matrikelnummer
      checkExistingMatrikelnummer(user);
    } else {
      console.log("[Already Completed] No user is signed in");
      showMatrikelnummerForm(); 
    }
  });
  
  function isValidMatrikelnummer(matrikelnummer) {
    return /^\d{6,8}$/.test(matrikelnummer);
  }
  
  submitButton.addEventListener("click", async function() {
    console.log("[Already Completed] Submit button clicked");
    
    // Get the matrikelnummer value
    const matrikelnummer = matrikelnummerInput.value.trim();
    
    // Validate input
    if (!matrikelnummer) {
      errorModal.show("Bitte gib eine Matrikelnummer ein.", "Eingabe fehlt");
      return;
    }
    
    if (!isValidMatrikelnummer(matrikelnummer)) {
      errorModal.show("Bitte gib eine gültige Matrikelnummer ein (6-8 Ziffern).", "Ungültige Eingabe");
      return;
    }
    
    // Determine if this is an update or new submission for loading text
    const isUpdate = submitButton.querySelector(".button-text").textContent === "Matr. aktualisieren";
    console.log("[Already Completed] Is this an update?", isUpdate);
    const buttonText = isUpdate ? "Matr. aktualisieren" : "Speichern";
    
    setButtonLoading(true, false, "submit-btn", buttonText);
    
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Already Completed] Error: No authenticated user found");
        errorModal.show(error_texts.error_texts.firebase_errors.firebase_auth_no_user_error);
        setButtonLoading(false, true, "submit-btn", buttonText);
        return;
      }
      
      const userDocRef = doc(db, "users", user.displayName);
      
      try {
        await updateDoc(userDocRef, {
          "studyCompensation": {
            matrikelnummer: matrikelnummer,
            submittedAt: serverTimestamp()
          }
        });
        
        console.log("[Already Completed] Matrikelnummer saved successfully");
        
        // Finish loading state
        setButtonLoading(false, false, "submit-btn", buttonText);
        
        // Show success message with appropriate text
        successMessage.textContent = isUpdate 
          ? "Deine Matrikelnummer wurde erfolgreich aktualisiert."
          : "Deine Matrikelnummer wurde erfolgreich gespeichert.";
        successMessage.classList.remove("d-none");
        
        // Disable input and button after successful submission
        matrikelnummerInput.disabled = true;
        submitButton.disabled = true;
        
      } catch (error) {
        console.error("[Already Completed] Error updating document:", error);
        errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_update_error);
        setButtonLoading(false, true, "submit-btn", buttonText);
      }
    } catch (error) {
      console.error("[Already Completed] Error:", error);
      errorModal.show("Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut.");
      setButtonLoading(false, true, "submit-btn", buttonText);
    }
  });
  
  matrikelnummerInput.addEventListener("input", function() {
    if (submitButton.classList.contains("btn-danger")) {
      submitButton.classList.remove("btn-danger");
      submitButton.disabled = false;
      
      const matrikelnummerText = matrikelnummerForm.querySelector("p.text-center");
      const isUpdate = matrikelnummerText.textContent.includes("aktualisieren");
      console.log("[Already Completed] Is input change in update mode?", isUpdate);
      submitButton.querySelector(".button-text").textContent = isUpdate 
        ? "Matr. aktualisieren" 
        : "Speichern";
    }
    
    if (!successMessage.classList.contains("d-none")) {
      successMessage.classList.add("d-none");
    }
  });
}); 