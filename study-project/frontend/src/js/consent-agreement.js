import { auth, db } from "./firebase-services.js";
import {
  doc,
  updateDoc,
  serverTimestamp,
  getDoc,
} from "firebase/firestore";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';
import Cookies from 'js-cookie';

document.addEventListener("DOMContentLoaded", function() {
  console.log("[Consent] DOM fully loaded and parsed");

  const consentCheckbox = document.getElementById("consent-checkbox");
  const continueButton = document.getElementById("continue-btn");
  
  function handleCheckboxChange() {
    if (continueButton.classList.contains('btn-danger')) {
      continueButton.disabled = true;
    } else {
      continueButton.disabled = !consentCheckbox.checked;
    }
  }
  
  consentCheckbox.addEventListener("change", handleCheckboxChange);
  
  handleCheckboxChange();

  async function checkIfConsentAlreadyGiven() {
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Consent] Error: No authenticated user found when checking consent status");
        return false;
      }
      
      const userDocRef = doc(db, "users", user.displayName);
      const userDocSnap = await getDoc(userDocRef);
      
      if (!userDocSnap.exists()) {
        console.log("[Consent] User document does not exist yet");
        return false;
      }
      
      const userData = userDocSnap.data();
      return userData && userData.consentGiven === true;
    } catch (error) {
      console.error("[Consent] Error checking if consent already given:", error);
      return false;
    }
  }

  auth.onAuthStateChanged(async (user) => {
    if (user) {
      const consentAlreadyGiven = await checkIfConsentAlreadyGiven();
      if (consentAlreadyGiven) {
        console.log("[Consent] Consent already given, redirecting to pre-study page");
        window.location.href = "/pre-study";
      }
    }
  });

  continueButton.addEventListener("click", async function () {
    console.log("[Consent] Continue button clicked");
    if (!consentCheckbox.checked) {
      errorModal.show(error_texts.error_texts.consent.consent_required, "Consent Required");
      return;
    }
    
    setButtonLoading(true, false, "continue-btn");

    const consentAlreadyGiven = await checkIfConsentAlreadyGiven();
    if (consentAlreadyGiven) {
      console.log("[Consent] Consent has already been given previously");
      errorModal.show("Du hast deine Einwilligung bereits erteilt. Du wirst zur nächsten Seite weitergeleitet.", "Einwilligung bereits erteilt");
      setTimeout(() => {
        window.location.href = "/pre-study";
      }, 2000); 
      return;
    }

    try {
      const user = auth.currentUser;
      let userDocRef; 
      
      if (!user) {
        console.error("[Consent] Error: No authenticated user found");
        errorModal.show(error_texts.error_texts.firebase_errors.firebase_auth_no_user_error);
        setButtonLoading(false, true, "continue-btn");
        return;
      }
      
      try {
        userDocRef = doc(db, "users", user.displayName); // Assign rather than declare
        console.log("[Consent] User Doc Ref:", userDocRef);
      } catch (error) {
        console.error("[Consent] Error creating document reference:", error);
        errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_ref_error);
        setButtonLoading(false, true, "continue-btn");
        return;
      }
      
      try {
        const userDocSnap = await getDoc(userDocRef);
        console.log("[Consent] User Doc Snap:", userDocSnap);
      } catch (error) {
        console.error("[Consent] Error getting document snapshot:", error);
        errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_snap_error);
        setButtonLoading(false, true, "continue-btn");
        return;
      }
      
      try {
        await updateDoc(userDocRef, {
          consentGiven: true,
          consentTimestamp: serverTimestamp(),
        });
        Cookies.set("consent-given", true, {
          path: "/"
        });
        console.log("[Consent] User consent updated successfully");
        setButtonLoading(false, false, "continue-btn");

        console.log("[Consent] Proceeding to pre-study questionnaire...");
        window.location.href = "/pre-study";
      } catch (error) {
        console.error("[Consent] Error updating document:", error);
        errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_update_error);
        setButtonLoading(false, true, "continue-btn");
        return;
      }
    } catch (error) {
      console.error("[Consent] Error getting authentication and user:", error);
      errorModal.show(error_texts.error_texts.firebase_errors.firebase_auth_no_user_error);
      setButtonLoading(false, true, "continue-btn");
      return;
    }
  });
});
