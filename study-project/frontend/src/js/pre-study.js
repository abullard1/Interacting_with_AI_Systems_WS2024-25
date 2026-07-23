import { auth, db } from "./firebase-services.js";
import { doc, updateDoc, serverTimestamp, getDoc } from "firebase/firestore";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';
import Cookies from 'js-cookie';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('pre-study-form');
  
  document.querySelectorAll('input[type="range"]').forEach(slider => {
    const display = slider.closest('.row').querySelector('.value-display');
    if (display) {
      display.textContent = slider.value;
      slider.addEventListener('input', () => {
        display.textContent = slider.value;
      });
    }
  });

  const expectationsText = document.getElementById('openExpectations');
  const expectationsCharCount = expectationsText ? expectationsText.closest('.form-group').querySelector('.form-text span') : null;
  if (expectationsText && expectationsCharCount) {
    expectationsCharCount.textContent = expectationsText.value.length;
    expectationsText.addEventListener('input', () => {
      expectationsCharCount.textContent = expectationsText.value.length;
    });
  }
  
  const aiHealthUsageDetails = document.getElementById('aiHealthUsageDetails');
  const aiHealthUsageCharCount = aiHealthUsageDetails ? aiHealthUsageDetails.closest('.form-group').querySelector('.form-text span') : null;
  if (aiHealthUsageDetails && aiHealthUsageCharCount) {
    aiHealthUsageCharCount.textContent = aiHealthUsageDetails.value.length;
    aiHealthUsageDetails.addEventListener('input', () => {
      aiHealthUsageCharCount.textContent = aiHealthUsageDetails.value.length;
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
  
  async function checkIfPreStudyAlreadyCompleted() {
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Pre-Study] Error: No authenticated user found when checking pre-study status");
        return false;
      }
      
      const studyToken = user.displayName;
      if (!studyToken) {
        console.error("[Pre-Study] Error: No study token found when checking pre-study status");
        return false;
      }
      
      const userDocRef = doc(db, "users", studyToken);
      const userDocSnap = await getDoc(userDocRef);
      
      if (!userDocSnap.exists()) {
        console.log("[Pre-Study] User document does not exist yet");
        return false;
      }
      
      const userData = userDocSnap.data();
      return userData && userData.preStudyQuestionnaire && userData.preStudyQuestionnaire.completed === true;
    } catch (error) {
      console.error("[Pre-Study] Error checking if pre-study already completed:", error);
      return false;
    }
  }
  
  auth.onAuthStateChanged(async (user) => {
    if (user) {
      const preStudyAlreadyCompleted = await checkIfPreStudyAlreadyCompleted();
      if (preStudyAlreadyCompleted) {
        console.log("[Pre-Study] Pre-study questionnaire already completed, redirecting to token page");
        window.location.href = "/token";
      }
    }
  });
  
  async function saveFormDataToFirebase(formData) {
    try {
      const user = auth.currentUser;
      if (!user) {
        console.error("[Pre-Study] Error: No authenticated user found.");
        errorModal.show(error_texts.error_texts.general.no_user_found);
        setButtonLoading(false, true, "continue-btn");
        return false;
      }

      const studyToken = user.displayName;
      if (!studyToken) {
        console.error("[Pre-Study] Error: No study token found.");
        errorModal.show(error_texts.error_texts.general.no_study_token);
        setButtonLoading(false, true, "continue-btn");
        return false;
      }

      const preStudyAlreadyCompleted = await checkIfPreStudyAlreadyCompleted();
      if (preStudyAlreadyCompleted) {
        console.log("[Pre-Study] Pre-study questionnaire has already been completed");
        errorModal.show("Du hast diesen Fragebogen bereits ausgefüllt. Du wirst zur nächsten Seite weitergeleitet.", "Fragebogen bereits ausgefüllt");
        setTimeout(() => {
          window.location.href = "/token";
        }, 2000);
        return false;
      }

      const userDocRef = doc(db, "users", studyToken);

      const preStudyData = {
        timestamp: serverTimestamp(),
        demographics: {
          age: parseInt(formData.get('age')),
          gender: formData.get('gender'),
          education: formData.get('education'),
          nativeLanguage: formData.get('nativeLanguage')
        },
        digitalConfidence: parseInt(formData.get('digitalConfidence')),
        aiExperience: {
          frequency: formData.get('aiFrequency'),
          healthUsage: formData.get('aiHealthUsage'),
          healthUsageDetails: formData.get('aiHealthUsageDetails')
        },
        aiTrust: {
          generalTrust: parseInt(formData.get('generalTrust')),
          accuracy: parseInt(formData.get('aiAccuracy')),
          comparedToHumans: formData.get('aiVsHuman')
        },
        healthLiteracy: {
          onlineSearchFrequency: formData.get('onlineSearchFrequency'),
          understandingAbility: parseInt(formData.get('understandingAbility')),
          trustSources: JSON.parse(formData.get('trustSources'))
        },
        expectations: {
          responsePreferences: JSON.parse(formData.get('responsePreferences')),
          speedImportance: parseInt(formData.get('speedImportance')),
          acceptSlower: parseInt(formData.get('acceptSlower')),
          openExpectations: formData.get('openExpectations') || null
        },
        deviceType: formData.get('deviceType'),
        completed: true
      };

      await updateDoc(userDocRef, {
        preStudyQuestionnaire: preStudyData,
        lastStage: "pre-study",
        studyStatus: "in_progress",
        lastActiveAt: serverTimestamp()
      });

      console.log("[Pre-Study] Successfully saved pre-study data to Firestore");
      return true;
    } catch (error) {
      console.error("[Pre-Study] Error saving data to Firestore:", error);
      errorModal.show(error_texts.error_texts.firebase_errors.firestore_write_error);
      return false;
    }
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    const isFormValid = form.checkValidity();
    
    const trustSourcesValid = validateCheckboxGroup('trustSourcesGroup');
    const responsePreferencesValid = validateCheckboxGroup('responsePreferencesGroup');
    
    form.classList.add('was-validated');
    
    if (!isFormValid || !trustSourcesValid || !responsePreferencesValid) {
      let firstInvalid = form.querySelector(':invalid') || 
                         document.querySelector('.checkbox-group.is-invalid');
      
      if (firstInvalid) {
        const formGroup = firstInvalid.closest('.form-group') || firstInvalid;
        formGroup.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }
    
    console.log('[Pre-Study] Form is valid, preparing to save data');
    
    setButtonLoading(true, false, "continue-btn");
    
    const formData = new FormData(form);
    
    formData.set('trustSources', JSON.stringify(
      Array.from(document.querySelectorAll('input[name="trustSources"]:checked'))
        .map(cb => cb.value)
    ));
    
    formData.set('responsePreferences', JSON.stringify(
      Array.from(document.querySelectorAll('input[name="responsePreferences"]:checked'))
        .map(cb => cb.value)
    ));
    
    const saveSuccess = await saveFormDataToFirebase(formData);
    
    if (saveSuccess) {
      Cookies.set("pre-study-completed", "true", { path: '/' });
      console.log('[Pre-Study] Marked pre-study as completed');
      
      console.log('[Pre-Study] Successfully saved data, redirecting to token page');
      window.location.href = '/token';
    } else {
      setButtonLoading(false, true, "continue-btn");
    }
  });
});