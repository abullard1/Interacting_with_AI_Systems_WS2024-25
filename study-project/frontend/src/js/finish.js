/**
 * Finish Page Controller
 */

import confetti from 'canvas-confetti';
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

console.log("[Finish Page] finish.js loaded.");

document.addEventListener("DOMContentLoaded", function() {
  console.log("[Finish] DOM fully loaded and parsed");

  Cookies.set("study-completed", "true", { expires: 365, path: '/' });
  console.log("[Finish] Set final study-completed cookie on page load to mark full completion");

  markStudyAsCompleted();
  
  // Trigger confetti celebration effect
  triggerConfettiCelebration();
  
  // Get DOM elements
  const matrikelnummerInput = document.getElementById("matrikelnummer");
  const submitButton = document.getElementById("submit-btn");
  const successMessage = document.getElementById("success-message");
  const matrikelnummerForm = document.getElementById("matrikelnummer-form");
  const loadingSpinner = document.getElementById("loading-spinner");
  
  async function markStudyAsCompleted() {
    try {
      const user = auth.currentUser;
      if (!user) {
        console.log("[Finish] No user found when marking study as completed. Will try again when auth state changes.");
        return;
      }
      
      const studyToken = user.displayName;
      if (!studyToken) {
        console.error("[Finish] Error: No study token found when marking study as completed");
        return;
      }
      
      const userDocRef = doc(db, "users", studyToken);
      await updateDoc(userDocRef, {
        studyStatus: "completed",
        lastStage: "finish",
        completionTimestamp: serverTimestamp(),
        lastActiveAt: serverTimestamp()
      });
      
      console.log("[Finish] Successfully marked study as completed in Firebase");
      
      try {
        const response = await fetch("/api/submit-study", {
          method: "POST"
        });

        if (!response.ok) {
          console.error(`[Finish] HTTP error releasing locks! status: ${response.status}`);
        } else {
          console.log("[Finish] API call successful, locks should be released");
        }
      } catch (error) {
        console.error("[Finish] Error making API call to release locks:", error);
      }
    } catch (error) {
      console.error("[Finish] Error marking study as completed:", error);
    }
  }
  
  function triggerConfettiCelebration() {
    console.log("[Finish] Triggering confetti celebration");
    
    confetti({
      particleCount: 120,
      spread: 80,
      angle: 90,
      origin: { x: 0.5, y: 1 },
      colors: ['#0d6efd', '#ffffff']
    });

    confetti({
      particleCount: 120,
      spread: 80,
      angle: 60,
      origin: { x: 0.7, y: 1 },
      colors: ['#0d6efd', '#ffffff']
    });

    confetti({
      particleCount: 120,
      spread: 80,
      angle: 120,
      origin: { x: 0.3, y: 1 },
      colors: ['#0d6efd', '#ffffff']
    });
  }
  

  function showMatrikelnummerForm() {
    console.log("[Finish] Showing Matrikelnummer form");
    loadingSpinner.classList.add("d-none");
    matrikelnummerForm.classList.remove("d-none");
  }
  
  async function checkExistingMatrikelnummer(user) {
    console.log("[Finish] Checking for existing Matrikelnummer for user:", user);
    
    try {
      if (!user) {
        console.error("[Finish] Error: No authenticated user found when checking existing Matrikelnummer");
        showMatrikelnummerForm(); 
        return;
      }
      
      const userDocRef = doc(db, "users", user.displayName);
      console.log("[Finish] User document reference:", userDocRef);
      
      const userDoc = await getDoc(userDocRef);
      console.log("[Finish] User document exists:", userDoc.exists());
      
      if (userDoc.exists()) {
        const userData = userDoc.data();
        console.log("[Finish] User data:", userData);
        
        if (userData.studyCompensation && userData.studyCompensation.matrikelnummer) {
          console.log("[Finish] Existing Matrikelnummer found:", userData.studyCompensation.matrikelnummer);
          
          const matrikelnummerText = matrikelnummerForm.querySelector("p.text-center");
          matrikelnummerText.textContent = "Du hast bereits eine Matrikelnummer eingetragen. Du kannst sie hier aktualisieren, falls nötig:";
          
          matrikelnummerInput.value = userData.studyCompensation.matrikelnummer;
          
          submitButton.querySelector(".button-text").textContent = "Matr. aktualisieren";
          
          console.log("[Finish] UI updated for existing Matrikelnummer");
        } else {
          console.log("[Finish] No existing Matrikelnummer found in user data");
        }
      } else {
        console.log("[Finish] User document does not exist");
      }
      
      showMatrikelnummerForm();
      
    } catch (error) {
      console.error("[Finish] Error checking for existing Matrikelnummer:", error);
      
      showMatrikelnummerForm();
    }
  }
  
  let authCheckTimeout = setTimeout(() => {
    console.log("[Finish] Auth check timeout reached, showing form");
    showMatrikelnummerForm(); 
  }, 5000); 
  
  onAuthStateChanged(auth, (user) => {
    console.log("[Finish] Auth state changed, user:", user);
    clearTimeout(authCheckTimeout); 
    
    if (user) {
      checkExistingMatrikelnummer(user);
      markStudyAsCompleted();
    } else {
      console.log("[Finish] No user is signed in");
      errorModal.show(error_texts.error_texts.firebase_errors.firebase_auth_no_user_error);
    }
  });
  
  function isValidMatrikelnummer(matrikelnummer) {
    return /^\d{6,8}$/.test(matrikelnummer);
  }
  
  submitButton.addEventListener("click", async function() {
    console.log("[Finish] Submit button clicked");
    
    const matrikelnummer = matrikelnummerInput.value.trim();
    
    if (!matrikelnummer) {
      errorModal.show("Bitte gib eine Matrikelnummer ein.", "Eingabe fehlt");
      return;
    }
    
    if (!isValidMatrikelnummer(matrikelnummer)) {
      errorModal.show("Bitte gib eine gültige Matrikelnummer ein (6-8 Ziffern).", "Ungültige Eingabe");
      return;
    }
    
    const isUpdate = submitButton.querySelector(".button-text").textContent === "Matr. aktualisieren";
    console.log("[Finish] Is this an update?", isUpdate);
    const buttonText = isUpdate ? "Matr. aktualisieren" : "Speichern";
    
    setButtonLoading(true, false, "submit-btn", buttonText);
    
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Finish] Error: No authenticated user found");
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
        
        console.log("[Finish] Matrikelnummer saved successfully");
        
        setButtonLoading(false, false, "submit-btn", buttonText);
        
        successMessage.textContent = isUpdate 
          ? "Deine Matrikelnummer wurde erfolgreich aktualisiert."
          : "Deine Matrikelnummer wurde erfolgreich gespeichert.";
        successMessage.classList.remove("d-none");
        
        matrikelnummerInput.disabled = true;
        submitButton.disabled = true;
        
      } catch (error) {
        console.error("[Finish] Error updating document:", error);
        errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_update_error);
        setButtonLoading(false, true, "submit-btn", buttonText);
      }
    } catch (error) {
      console.error("[Finish] Error:", error);
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
      console.log("[Finish] Is input change in update mode?", isUpdate);
      submitButton.querySelector(".button-text").textContent = isUpdate 
        ? "Matr. aktualisieren" 
        : "Speichern";
    }
    
    if (!successMessage.classList.contains("d-none")) {
      successMessage.classList.add("d-none");
    }
  });
});
