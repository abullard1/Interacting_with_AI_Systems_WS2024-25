
import { app } from "./initialize-firebase.js";
import { auth, db } from "./firebase-services.js";
import { signInAnonymously, updateProfile } from "firebase/auth";
import {
  doc,
  setDoc,
  getDoc,
  updateDoc,
  serverTimestamp,
} from "firebase/firestore";
import Cookies from "js-cookie";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';
import { setButtonLoading } from './loading-button-change.js';

document.addEventListener('DOMContentLoaded', () => {
  const continueButton = document
  .getElementById("continue-btn");
  
  continueButton.addEventListener("click", async function () {
    console.log("[Introduction] Continue button clicked");
    setButtonLoading(true, false, "continue-btn");

    try {
      const study_token = Cookies.get("study_token");
      if (!study_token) {
        console.error("[Introduction] Error: No study token found in cookies.");
        errorModal.show(error_texts.error_texts.introduction.missing_study_token_error);
        setButtonLoading(false, true, "continue-btn");
        return;
      }

      try {
        let user = auth.currentUser;
        if (!user) {
          try {
            const { user: anonUser } = await signInAnonymously(auth);
            user = anonUser;
            console.log("[Introduction] Signed in anonymously:", user);
          } catch (error) {
            console.error("[Introduction] Error signing in anonymously:", error);
            errorModal.show(error_texts.error_texts.firebase_errors.firebase_auth_sign_in_error);
            setButtonLoading(false, true, "continue-btn");
            return;
          }
        } else {
          console.log("[Introduction] User already signed in.");
        }

        if (user.displayName !== study_token) {
          try {
            await updateProfile(user, { displayName: study_token });
            console.log("[Introduction] User profile updated successfully:", user);
          } catch (error) {
            console.error("[Introduction] Error updating the user profile:", error);
            errorModal.show(error_texts.error_texts.firebase_errors.firebase_auth_sign_in_error);
            setButtonLoading(false, true, "continue-btn");
            return;
          }
        }

        const device_info = navigator.userAgent;
        console.log("[Introduction] Device Info:", device_info);
        let userDocRef;
        try {
          userDocRef = doc(db, "users", study_token);
          console.log("[Introduction] User Doc Ref:", userDocRef);
        } catch (error) {
          console.error("[Introduction] Error getting the Firebase Firestore User Document Reference:", error);
          errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_ref_error);
          setButtonLoading(false, true, "continue-btn");
          return;
        }
        let userDocSnap;
        try {
          userDocSnap = await getDoc(userDocRef);
          console.log("[Introduction] User Doc Snap:", userDocSnap);
        } catch (error) {
          console.error("[Introduction] Error getting the Firebase Firestore User Document Snapshot:", error);
          errorModal.show(error_texts.error_texts.firebase_errors.firestore_user_doc_snap_error);
          setButtonLoading(false, true, "continue-btn");
          return;
        }
        console.log("[Introduction] User:", user);

        if (userDocSnap.exists()) {
          console.log("[Introduction] User Doc Snap exists:", userDocSnap);
          await updateDoc(userDocRef, {
            lastActiveAt: serverTimestamp(),
            "deviceInfo.deviceInfo": device_info,
            "deviceInfo.screenResolution": `${window.screen.width}x${window.screen.height}`,
          });
        } else {
          await setDoc(userDocRef, {
            studyToken: study_token,
            createdAt: serverTimestamp(),
            completionTimestamp: null,
            gradio_study_completion_timestamp: null,
            lastActiveAt: serverTimestamp(),
            lastStage: "introduction",
            consentGiven: false,
            consentTimestamp: null,
            studyStatus: "in_progress",
            deviceInfo: {
              deviceInfo: device_info,
              screenResolution: `${window.screen.width}x${window.screen.height}`,
            },
            preStudyQuestionnaire: {
              timestamp: null,
              demographics: {
                age: null,
                gender: null,
                education: null,
                nativeLanguage: null
              },
              digitalConfidence: null,
              aiExperience: {
                frequency: null,
                healthUsage: null,
                healthUsageDetails: null
              },
              aiTrust: {
                generalTrust: null,
                accuracy: null,
                comparedToHumans: null
              },
              healthLiteracy: {
                onlineSearchFrequency: null,
                understandingAbility: null,
                trustSources: []
              },
              expectations: {
                responsePreferences: [],
                speedImportance: null,
                acceptSlower: null,
                openExpectations: null
              },
              deviceType: null,
              completed: false
            },
            mainStudy: {
              submit_vs_loading_appear_time_difference: {},
              loading_to_response_time_difference: {},
              last_scenario_stage: null,
              gradio_app_finished: false,
              scenarios: {
                slow_easy: {
                  number_in_study_order: null,
                  scenario_title: null,
                  tokens_per_second: null,
                  feedback: {
                    wahrgenommeneGenauigkeit: null,
                    wahrgenommeneVollständigkeit: null,
                    wahrgenommeneNützlichkeit: null,
                    verständlichkeit: null,
                    vertrauenInDieAntwort: null,
                  }
                },
                fast_easy: {
                  number_in_study_order: null,
                  scenario_title: null,
                  tokens_per_second: null,
                  feedback: {
                    wahrgenommeneGenauigkeit: null,
                    wahrgenommeneVollständigkeit: null,
                    wahrgenommeneNützlichkeit: null,
                    verständlichkeit: null,
                    vertrauenInDieAntwort: null,
                  }
                },
                slow_hard: {
                  number_in_study_order: null,
                  scenario_title: null,
                  tokens_per_second: null,
                  feedback: {
                    wahrgenommeneGenauigkeit: null,
                    wahrgenommeneVollständigkeit: null,
                    wahrgenommeneNützlichkeit: null,
                    verständlichkeit: null,
                    vertrauenInDieAntwort: null,
                  }
                },
                fast_hard: {
                  number_in_study_order: null,
                  scenario_title: null,
                  tokens_per_second: null,
                  feedback: {
                    wahrgenommeneGenauigkeit: null,
                    wahrgenommeneVollständigkeit: null,
                    wahrgenommeneNützlichkeit: null,
                    verständlichkeit: null,
                    vertrauenInDieAntwort: null,
                  }
                }
              }
            },
            postStudyQuestionnaire: {
              timestamp: null,
              aiPerception: {
                trustworthiness: null,
                credibility: null,
                consistency: null
              },
              trustChange: {
                direction: null,
                reason: null,
                generalTrust: null,
                kiAccuracy: null,
                kiVsHuman: null
              },
              healthLiteracy: {
                understandingAbility: null,
                trustSources: []
              },
              answerPreferences: {
                preferredStyle: null,
                speedImportance: null,
                acceptSlowerForAccuracy: null
              },
              userExperience: {
                usabilityFrustration: null,
                kiThinking: null,
                responseTimeNatural: null
              },
              openFeedback: null,
              completed: false
            },
            studyCompensation: {
              matrikelnummer: null,
              submittedAt: null
            }
          });
        }
        console.log("[Introduction] User Doc Ref created:", userDocRef);
        setButtonLoading(false, false, "continue-btn");

        console.log("[Introduction] Proceeding to consent page...");
        window.location.href = "/consent";
      } catch (error) {
        console.error("[Introduction] Error during user registration:", error);
        errorModal.show(error_texts.error_texts.general_error);
        setButtonLoading(false, true, "continue-btn");
        return;
      }
    } catch (error) {
      console.error("[Introduction] Error during user registration:", error);
      errorModal.show(error_texts.error_texts.general_error);
      setButtonLoading(false, true, "continue-btn");
      return;
    }
  });
});
