import { auth, db } from "./firebase-services.js";
import Cookies from "js-cookie";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';
import { doc, updateDoc, serverTimestamp } from 'firebase/firestore';

document.addEventListener('DOMContentLoaded', () => {
  console.log("[Token] DOM fully loaded and parsed");

  const tokenField = document.getElementById('tokenField');
  const copyButton = document.getElementById('copyButton');
  const continueBtn = document.getElementById('continue-btn');
  
  const copyToast = new bootstrap.Toast(document.getElementById('copyToast'));

  function getStudyToken() {
    try {
      const studyToken = Cookies.get('study_token');
      console.log('[Token] Study token from cookie:', studyToken);
      
      if (!studyToken) {
        console.error('[Token] No study token found in cookies');
        errorModal.show(error_texts.error_texts.introduction.missing_study_token_error);
        setTimeout(() => {
          window.location.href = '/';
        }, 3000);
        return null;
      }
      
      return studyToken;
    } catch (error) {
      console.error('[Token] Error getting study token:', error);
      errorModal.show(error_texts.error_texts.general_error);
      return null;
    }
  }

  function copyToken() {
    try {
      navigator.clipboard.writeText(tokenField.value)
        .then(() => {
          copyToast.show();
          console.log('[Token] Token copied to clipboard');
        })
        .catch(err => {
          console.error('[Token] Error copying to clipboard:', err);
          errorModal.show(error_texts.error_texts.general_error);
        });
    } catch (error) {
      console.error('[Token] Error copying token:', error);
      errorModal.show(error_texts.error_texts.general_error);
    }
  }

  const studyToken = getStudyToken();
  if (studyToken) {
    tokenField.value = studyToken;
  }

  copyButton.addEventListener('click', copyToken);
  
  continueBtn.addEventListener('click', async () => {
    console.log('[Token] Navigating to Gradio app');
    
    setButtonLoading(true, false, "continue-btn");

    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Token] Error: No authenticated user found.");
        errorModal.show(error_texts.error_texts.general.no_user_found);
        setButtonLoading(false, true, "continue-btn");
        return;
      }
      const studyToken = user.displayName;
      if (!studyToken) {
        console.error("[Token] Error: No study token found.");
        errorModal.show(error_texts.error_texts.general.no_study_token);
        setButtonLoading(false, true, "continue-btn");
        return;
      }

      const userDocRef = doc(db, "users", studyToken);
      await updateDoc(userDocRef, {
        lastStage: "token",
        lastActiveAt: serverTimestamp()
      });

      Cookies.set("token-page-completed", "true", { path: '/' });
      
      console.log('[Token] Set cookie: token-page-completed=true');

      console.log('[Token] Successfully updated user document, navigating to study-explanation page');
      setTimeout(() => {
        window.location.href = '/study-explanation';
      }, 500);

    } catch (error) {
      console.error("[Token] Error updating user document:", error);
      setButtonLoading(false, true, "continue-btn");
      errorModal.show(error_texts.error_texts.general_error);
      return;
    }
  });
}); 