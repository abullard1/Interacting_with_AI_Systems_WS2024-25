/**
 * Study Explanation Page Controller
 */

import { auth, db } from "./firebase-services.js";
import { 
  doc, 
  updateDoc,
  serverTimestamp
} from "firebase/firestore";
import Cookies from "js-cookie";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';

document.addEventListener("DOMContentLoaded", function() {
    console.log("[Study Explanation] DOM fully loaded and parsed");
    
    initializeStudyExplanationPage();
});

function initializeStudyExplanationPage() {
    displayStudyToken();
    setupContinueButton();
}

function displayStudyToken() {
    const tokenDisplay = document.getElementById("token-display");
    if (!tokenDisplay) {
        console.error("[Study Explanation] Token display element not found");
        return;
    }
    
    try {
        const studyToken = Cookies.get('study_token');
        
        if (!studyToken) {
            console.error("[Study Explanation] Error: No study token found in cookies");
            tokenDisplay.textContent = "Nicht verfügbar";
            setTimeout(() => {
                window.location.href = '/token';
            }, 3000);
            return;
        }
        
        tokenDisplay.textContent = studyToken;
        console.log("[Study Explanation] Displayed user's study token from cookies");
        
    } catch (error) {
        console.error("[Study Explanation] Error displaying token:", error);
        tokenDisplay.textContent = "Nicht verfügbar";
    }
}

function setupContinueButton() {
    const continueBtn = document.getElementById("continue-btn");
    
    if (!continueBtn) {
        console.error("[Study Explanation] Continue button not found");
        return;
    }
    
    continueBtn.addEventListener("click", async () => {
        console.log("[Study Explanation] Continue button clicked");
        
        setButtonLoading(true, false, "continue-btn");
        
        try {
            const user = auth.currentUser;
            if (!user) {
                console.error("[Study Explanation] Error: No authenticated user found.");
                errorModal.show(error_texts.error_texts.general.no_user_found);
                setButtonLoading(false, true, "continue-btn");
                return;
            }
            
            const studyToken = user.displayName;
            if (!studyToken) {
                console.error("[Study Explanation] Error: No study token found.");
                errorModal.show(error_texts.error_texts.general.no_study_token);
                setButtonLoading(false, true, "continue-btn");
                return;
            }
            
            const userDocRef = doc(db, "users", studyToken);
            await updateDoc(userDocRef, {
                lastStage: "study-explanation",
                lastActiveAt: serverTimestamp()
            });
            
            Cookies.set("study-explanation-completed", "true", { path: '/' });
            
            console.log("[Study Explanation] Set cookie: study-explanation-completed");
            
            console.log("[Study Explanation] Redirecting to study page");
            setTimeout(() => {
                window.location.href = "/study";
            }, 500);
            
        } catch (error) {
            console.error("[Study Explanation] Error:", error);
            errorModal.show(error_texts.error_texts.general_error);
            setButtonLoading(false, true, "continue-btn");
        }
    });
} 