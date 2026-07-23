import { auth, db } from "./firebase-services.js";
import { doc, updateDoc, serverTimestamp, getDoc } from "firebase/firestore";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';
import Cookies from "js-cookie";

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('post-study-form');
  
  document.querySelectorAll('input[type="range"]').forEach(slider => {
    const display = slider.closest('.row').querySelector('.value-display');
    if (display) {
      display.textContent = slider.value;
      slider.addEventListener('input', () => {
        display.textContent = slider.value;
      });
    }
  });

  const trustChangeReasonText = document.getElementById('trustChangeReason');
  const reasonCharCount = document.getElementById('reasonCharCount');
  if (trustChangeReasonText && reasonCharCount) {
    reasonCharCount.textContent = trustChangeReasonText.value.length;
    trustChangeReasonText.addEventListener('input', () => {
      reasonCharCount.textContent = trustChangeReasonText.value.length;
    });
  }

  function validateCheckboxGroup(groupId) {
    const group = document.getElementById(groupId);
    const checkboxes = group.querySelectorAll('input[type="checkbox"]');
    const checked = Array.from(checkboxes).some(cb => cb.checked);
    
    if (!checked) {
      group.classList.add('is-invalid');
      return false;
    } else {
      group.classList.remove('is-invalid');
      return true;
    }
  }

  document.querySelectorAll('.no-answer-option').forEach(noAnswerCheckbox => {
    const name = noAnswerCheckbox.getAttribute('name');
    const group = noAnswerCheckbox.closest('.checkbox-group');
    const otherCheckboxes = group.querySelectorAll(`input[name="${name}"]:not(.no-answer-option)`);
    
    noAnswerCheckbox.addEventListener('change', () => {
      if (noAnswerCheckbox.checked) {
        otherCheckboxes.forEach(cb => {
          cb.checked = false;
          cb.disabled = true;
        });
      } else {
        otherCheckboxes.forEach(cb => {
          cb.disabled = false;
        });
      }
      validateCheckboxGroup(group.id);
    });
    
    otherCheckboxes.forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked && noAnswerCheckbox.checked) {
          noAnswerCheckbox.checked = false;
          otherCheckboxes.forEach(other => {
            other.disabled = false;
          });
        }
        validateCheckboxGroup(group.id);
      });
    });
  });

  const openFeedbackText = document.getElementById('openFeedback');
  const feedbackCharCount = document.getElementById('feedbackCharCount');
  if (openFeedbackText && feedbackCharCount) {
    feedbackCharCount.textContent = openFeedbackText.value.length;
    openFeedbackText.addEventListener('input', () => {
      feedbackCharCount.textContent = openFeedbackText.value.length;
    });
  }
  
  async function checkIfPostStudyAlreadyCompleted() {
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Post-Study] Error: No authenticated user found when checking post-study status");
        return false;
      }
      
      const studyToken = user.displayName;
      if (!studyToken) {
        console.error("[Post-Study] Error: No study token found when checking post-study status");
        return false;
      }
      
      const userDocRef = doc(db, "users", studyToken);
      const userDocSnap = await getDoc(userDocRef);
      
      if (!userDocSnap.exists()) {
        console.log("[Post-Study] User document does not exist yet");
        return false;
      }
      
      const userData = userDocSnap.data();
      return userData && userData.postStudyQuestionnaire && userData.postStudyQuestionnaire.completed === true;
    } catch (error) {
      console.error("[Post-Study] Error checking if post-study already completed:", error);
      return false;
    }
  }
  
  auth.onAuthStateChanged(async (user) => {
    if (user) {
      const postStudyAlreadyCompleted = await checkIfPostStudyAlreadyCompleted();
      if (postStudyAlreadyCompleted) {
        console.log("[Post-Study] Post-study questionnaire already completed, redirecting to finish page");
        window.location.href = "/finish";
      }
    }
  });
  
  async function saveFormDataToFirebase(formData) {
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Post-Study] Error: No authenticated user found.");
        errorModal.show(error_texts.error_texts.general.no_user_found);
        setButtonLoading(false, true, "continue-btn");
        return false;
      }

      const studyToken = user.displayName;
      if (!studyToken) {
        console.error("[Post-Study] Error: No study token found.");
        errorModal.show(error_texts.error_texts.general.no_study_token);
        setButtonLoading(false, true, "continue-btn");
        return false;
      }

      const postStudyAlreadyCompleted = await checkIfPostStudyAlreadyCompleted();
      if (postStudyAlreadyCompleted) {
        console.log("[Post-Study] Post-study questionnaire has already been completed");
        errorModal.show("Du hast diesen Fragebogen bereits ausgefüllt. Du wirst zur nächsten Seite weitergeleitet.", "Fragebogen bereits ausgefüllt");
        setTimeout(() => {
          window.location.href = "/finish";
        }, 2000);
        return false;
      }

      const userDocRef = doc(db, "users", studyToken);

      const postStudyData = {
        timestamp: serverTimestamp(),
        aiPerception: {
          trustworthiness: parseInt(formData.get('trustworthiness')),
          credibility: parseInt(formData.get('credibility')),
          consistency: parseInt(formData.get('consistency'))
        },
        trustChange: {
          direction: formData.get('trustChange'),
          reason: formData.get('trustChangeReason') || null,
          generalTrust: parseInt(formData.get('generalTrust')),
          kiAccuracy: parseInt(formData.get('kiAccuracy')),
          kiVsHuman: formData.get('kiVsHuman')
        },
        healthLiteracy: {
          understandingAbility: parseInt(formData.get('understandingAbility')),
          trustSources: JSON.parse(formData.get('trustSources'))
        },
        answerPreferences: {
          preferredStyle: formData.get('answerPreference'),
          speedImportance: parseInt(formData.get('speedImportance')),
          acceptSlowerForAccuracy: parseInt(formData.get('acceptSlower'))
        },
        userExperience: {
          usabilityFrustration: parseInt(formData.get('usabilityFrustration')),
          kiThinking: parseInt(formData.get('kiThinking')),
          responseTimeNatural: parseInt(formData.get('responseTimeNatural'))
        },
        openFeedback: formData.get('openFeedback') || null,
        completed: true
      };

      await updateDoc(userDocRef, {
        postStudyQuestionnaire: postStudyData,
        lastActiveAt: serverTimestamp(),
        lastStage: "post-study"
      });
      
      console.log("[Post-Study] Successfully saved post-study data to Firestore");
      return true;
    } catch (error) {
      console.error("[Post-Study] Error saving data to Firestore:", error);
      setButtonLoading(false, true, "continue-btn");
      errorModal.show(error_texts.error_texts.firebase_errors.firestore_write_error);
      return false;
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    const isFormValid = form.checkValidity();
    
    const trustSourcesValid = validateCheckboxGroup('trustSourcesGroup');
    
    form.classList.add('was-validated');
    
    if (!isFormValid || !trustSourcesValid) {
      const firstInvalid = form.querySelector(':invalid') || 
                          document.querySelector('.checkbox-group.is-invalid');
      
      if (firstInvalid) {
        const formGroup = firstInvalid.closest('.form-group') || firstInvalid;
        formGroup.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }
    
    console.log('[Post-Study] Form is valid, preparing to save data');
    
    setButtonLoading(true, false, "continue-btn");
    
    const formData = new FormData(form);
    
    formData.set('trustSources', JSON.stringify(
      Array.from(document.querySelectorAll('input[name="trustSources"]:checked'))
        .map(cb => cb.value)
    ));
    
    const saveSuccess = await saveFormDataToFirebase(formData);
    
    if (saveSuccess) {
      Cookies.set("post-study-completed", "true", { expires: 365, path: '/' });
      console.log('[Post-Study] Marked post-study as completed');
      
      console.log('[Post-Study] Successfully saved data, redirecting to finish page');
      window.location.href = '/finish';
    } else {
      setButtonLoading(false, true, "continue-btn");
    }
  });
});
