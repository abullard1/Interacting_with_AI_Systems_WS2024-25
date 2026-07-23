/**
 * Study Page Controller
 */

import { auth, db } from "./firebase-services.js";
import { 
  doc, 
  updateDoc,
  serverTimestamp,
  arrayUnion,
  getDoc
} from "firebase/firestore";
import Cookies from "js-cookie";
import { errorModal } from './components/ErrorModal.js';
import error_texts from './error-texts.json';

document.addEventListener("DOMContentLoaded", function() {
    console.log("[Study] DOM fully loaded and parsed");
    initializeStudyPage();
});

let scenario_stage = 1;
let observerTimeout = null;

function initializeGradioSetupLoader() {
    const overlay = document.createElement('div');
    overlay.className = 'gradio-loading-overlay';
    overlay.id = 'gradio-loading-overlay';

    const content = document.createElement('div');
    content.className = 'gradio-loading-content';

    const spinner = document.createElement('div');
    spinner.className = 'spinner-border gradio-loading-spinner text-primary';
    spinner.setAttribute('role', 'status');

    const srOnly = document.createElement('span');
    srOnly.className = 'visually-hidden';
    srOnly.textContent = 'Loading...';
    spinner.appendChild(srOnly);

    const loadingText = document.createElement('div');
    loadingText.className = 'gradio-loading-text';
    loadingText.textContent = 'KI-Interface wird geladen...';

    content.appendChild(spinner);
    content.appendChild(loadingText);
    overlay.appendChild(content);
    document.body.appendChild(overlay);
}

async function initializeStudyPage() {
    initializeGradioSetupLoader();
    
    try {
        const user = auth.currentUser;
        if (user) {
            const studyToken = user.displayName;
            if (studyToken) {
                const userDocRef = doc(db, "users", studyToken);
                const docSnap = await getDoc(userDocRef);
                
                if (docSnap.exists() && docSnap.data().mainStudy?.last_scenario_stage) {
                    scenario_stage = docSnap.data().mainStudy.last_scenario_stage;
                    console.log("[Study] Restored scenario stage from Firebase:", scenario_stage);
                }
            }
        }
    } catch (error) {
        console.error("[Study] Error retrieving scenario stage:", error);
    }
    
    setupGradioIntegration();
}

function setupGradioIntegration() {
    const maxRetries = 10;
    let retryCount = 0;
    
    function trySetupGradio() {
        const gradioApp = document.querySelector("gradio-app");
        if (gradioApp) {
            setupGradioEventListeners(gradioApp);
        } else if (retryCount < maxRetries) {
            retryCount++;
            setTimeout(trySetupGradio, 500);
        } else {
            console.error("[Study] Failed to find Gradio app after", maxRetries, "attempts");
            errorModal.show(error_texts.error_texts.study.gradio_error);
        }
    }
    
    trySetupGradio();
}

function setupGradioEventListeners(gradioApp) {
    gradioApp.addEventListener("error", (error) => {
        console.error("[Study] Gradio error:", error);
        errorModal.show(error_texts.error_texts.study.gradio_error);
        const overlay = document.getElementById('gradio-loading-overlay');
        if (overlay) overlay.remove();
    });

    gradioApp.addEventListener("render", () => {
        console.log("[Study] Gradio app is ready");
        
        const overlay = document.getElementById('gradio-loading-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }

        cleanupGradioUI();
        setupNextScenarioButton();
        setupClickTimestamps();
        
        updateProgressBar(scenario_stage);
        
        setTimeout(() => {
            const btn = document.querySelector("#next-scenario-btn");
            if (btn) {
                console.log("[Study] Button found after render:");
                console.log("[Study] - Text:", btn.textContent.trim());
                console.log("[Study] - Classes:", btn.className);
                console.log("[Study] - Visible:", btn.offsetParent !== null);
                console.log("[Study] - Has completion class:", btn.classList.contains("study-completed-btn"));
            } else {
                console.log("[Study] Button not found after render");
            }
        }, 1000);
    }, { once: true });
}

function setupClickTimestamps() {
    const sendBtn = document.querySelector("#send-btn");
    if (sendBtn) {
        sendBtn.addEventListener("click", async () => {
            // Record the button click timestamp
            const clickTimestamp = Date.now();
            console.log("[Study] Click timestamp:", clickTimestamp);
            let loadingAppearTimestamp = null;
            let loadingObserverDisconnected = false;

            const loadingObserver = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.addedNodes.length) {
                        const loadingIndicator = document.querySelector(".message.bot.pending.bubble");
                        if (loadingIndicator && !loadingAppearTimestamp) {
                            loadingAppearTimestamp = Date.now();
                            const appearTimeDifference = loadingAppearTimestamp - clickTimestamp;
                            console.log("[Study] Loading indicator appeared after:", appearTimeDifference, "ms");
                            
                            loadingIndicator.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            
                            saveClickToLoadingTimeToFirebase(appearTimeDifference);
                            
                        }
                    }
                    
                    if (mutation.type === 'childList' && loadingAppearTimestamp && !loadingObserverDisconnected) {
                        const loadingIndicator = document.querySelector(".message.bot.pending.bubble");
                        
                        const messageContents = document.querySelectorAll(".message-content");
                        const thirdMessageContent = messageContents[2];
                        
                        if (thirdMessageContent && 
                            thirdMessageContent.textContent.trim().length > 0 && 
                            !loadingIndicator) {
                            
                            // Loading indicator is gone and assistant message with content is present
                            const responseTimestamp = Date.now();
                            const responseTime = responseTimestamp - loadingAppearTimestamp;
                            console.log("[Study] Assistant response appeared after:", responseTime, "ms from loading indicator");
                            
                            // Save the response time to Firebase
                            saveLoadingToResponseTimeToFirebase(responseTime);
                            
                            // Clear timeout if it exists
                            if (observerTimeout) {
                                clearTimeout(observerTimeout);
                                observerTimeout = null;
                            }
                            
                            // Disconnect observer once we've detected both events
                            loadingObserver.disconnect();
                            loadingObserverDisconnected = true;
                        }
                    }
                }
            });
            
            observerTimeout = setTimeout(() => {
                if (!loadingObserverDisconnected) {
                    console.warn("[Study] Observer timeout reached after 30 seconds - disconnecting");
                    loadingObserver.disconnect();
                    loadingObserverDisconnected = true;
                    
                    logObserverTimeoutToFirebase();
                }
            }, 30000);
            
            const chatContainer = document.querySelector(".chat-section") || 
                                document.querySelector("#chat-container") || 
                                document.querySelector("gradio-app");
            
            if (chatContainer) {
                loadingObserver.observe(chatContainer, { childList: true, subtree: true, attributes: true });
            }

            try {
              const user = auth.currentUser;
              if (!user) {
                console.error("[Study] Error: No authenticated user found.");
                errorModal.show(error_texts.error_texts.general.no_user_found);
                return;
              }

              const studyToken = user.displayName;
              if (!studyToken) {
                console.error("[Study] Error: No study token found.");
                errorModal.show(error_texts.error_texts.general.no_study_token);
                return;
              }

              const userDocRef = doc(db, "users", studyToken);
              await updateDoc(userDocRef, {
                lastStage: "study",
                lastActiveAt: serverTimestamp(),
                studyStatus: "in_progress"
              });
              
            } catch (error) {
              console.error("[Study] Error updating timestamps:", error);
              errorModal.show(error_texts.error_texts.general_error);
            }
        });
    }
}

async function logObserverTimeoutToFirebase() {
    try {
        const user = auth.currentUser;
        if (!user) {
            console.error("[Study] Error: No authenticated user found.");
            return;
        }

        const studyToken = user.displayName;
        if (!studyToken) {
            console.error("[Study] Error: No study token found.");
            return;
        }

        const currentStage = scenario_stage || 1;

        if (!scenario_stage || scenario_stage < 1 || scenario_stage > 4) {
            console.warn(`[Study] Unexpected scenario_stage value: ${scenario_stage}, using ${currentStage} instead`);
        }
        
        const userDocRef = doc(db, "users", studyToken);
        
        const updateData = {};
        updateData[`mainStudy.observer_timeouts.stage_${currentStage}`] = Date.now();
        
        await updateDoc(userDocRef, updateData);
        console.log(`[Study] Logged observer timeout for stage ${currentStage}`);
    } catch (error) {
        console.error("[Study] Error logging observer timeout:", error);
    }
}

async function saveClickToLoadingTimeToFirebase(timeDifference) {
    try {
        const user = auth.currentUser;
        if (!user) {
            console.error("[Study] Error: No authenticated user found.");
            return;
        }

        const studyToken = user.displayName;
        if (!studyToken) {
            console.error("[Study] Error: No study token found.");
            return;
        }

        const currentStage = scenario_stage || 1;

        if (!scenario_stage || scenario_stage < 1 || scenario_stage > 4) {
            console.warn(`[Study] Unexpected scenario_stage value: ${scenario_stage}, using ${currentStage} instead`);
        }
        
        const userDocRef = doc(db, "users", studyToken);
        
        const updateData = {};
        updateData[`mainStudy.submit_vs_loading_appear_time_difference.stage_${currentStage}`] = timeDifference;
        
        await updateDoc(userDocRef, updateData);
        console.log(`[Study] Saved click-to-loading time for stage ${currentStage}: ${timeDifference}ms`);
    } catch (error) {
        console.error("[Study] Error saving click-to-loading time:", error);
    }
}

async function saveLoadingToResponseTimeToFirebase(timeDifference) {
    try {
        const user = auth.currentUser;
        if (!user) {
            console.error("[Study] Error: No authenticated user found.");
            return;
        }

        const studyToken = user.displayName;
        if (!studyToken) {
            console.error("[Study] Error: No study token found.");
            return;
        }

        const currentStage = scenario_stage || 1;

        if (!scenario_stage || scenario_stage < 1 || scenario_stage > 4) {
            console.warn(`[Study] Unexpected scenario_stage value: ${scenario_stage}, using ${currentStage} instead`);
        }

        const userDocRef = doc(db, "users", studyToken);

        const updateData = {};
        updateData[`mainStudy.loading_to_response_time_difference.stage_${currentStage}`] = timeDifference;
        updateData["lastActiveAt"] = serverTimestamp();

        await updateDoc(userDocRef, updateData);

        console.log(`[Study] Successfully saved loading-to-response time for stage ${currentStage}: ${timeDifference}ms`);
    } catch (error) {
        console.error("[Study] Error saving loading-to-response time to Firebase:", error);
    }
}

async function updateScenarioStage(newStage) {
    scenario_stage = newStage;
    console.log("[Study] Updated scenario stage to:", scenario_stage);
    
    updateProgressBar(scenario_stage);
    
    try {
        const user = auth.currentUser;
        if (!user) {
            console.error("[Study] Error: No user found for saving scenario stage");
            return;
        }

        const studyToken = user.displayName;
        if (!studyToken) {
            console.error("[Study] Error: No study token found");
            return;
        }

        const userDocRef = doc(db, "users", studyToken);
        await updateDoc(userDocRef, {
            "mainStudy.last_scenario_stage": scenario_stage
        });
        console.log("[Study] Saved scenario stage to Firebase:", scenario_stage);
    } catch (error) {
        console.error("[Study] Error saving scenario stage to Firebase:", error);
    }
}

function cleanupGradioUI() {
    console.log("[Study] Starting UI cleanup...");
    
    removeTrashIcons();
    
    setupIconRemovalObserver();
    
    setTimeout(removeTrashIcons, 1000);
    setTimeout(removeTrashIcons, 3000);
}

function removeTrashIcons() {
    try {
        const selectors = [
            ".icon-button-wrapper.top-panel.hide-top-corner",
            ".icon-button-wrapper.top-panel",
            "button[title='Clear']",
            "button[aria-label='Clear']"
        ];
        
        let removedCount = 0;
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                console.log(`[Study] Found trash icon with selector: ${selector}`, element);
                element.remove();
                removedCount++;
            });
        });
        
        const iframes = document.querySelectorAll("iframe");
        iframes.forEach(iframe => {
            try {
                const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
                selectors.forEach(selector => {
                    const elements = iframeDocument.querySelectorAll(selector);
                    elements.forEach(element => {
                        console.log(`[Study] Found trash icon in iframe with selector: ${selector}`, element);
                        element.remove();
                        removedCount++;
                    });
                });
            } catch (err) {
            }
        });
        
        const gradioApp = document.querySelector("gradio-app");
        if (gradioApp && gradioApp.shadowRoot) {
            selectors.forEach(selector => {
                const elements = gradioApp.shadowRoot.querySelectorAll(selector);
                elements.forEach(element => {
                    console.log(`[Study] Found trash icon in shadow DOM with selector: ${selector}`, element);
                    element.remove();
                    removedCount++;
                });
            });
        }
        
        if (removedCount > 0) {
            console.log(`[Study] Successfully removed ${removedCount} trash icon(s)`);
        } else {
            console.log("[Study] No trash icons found to remove");
        }
    } catch (error) {
        console.error("[Study] Error removing trash icons:", error);
    }
}

function setupIconRemovalObserver() {
    try {
        const iconObserver = new MutationObserver((mutations) => {
            let foundNewIcons = false;
            
            for (const mutation of mutations) {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) {
                            if (node.classList && 
                                (node.classList.contains("icon-button-wrapper") || 
                                 node.getAttribute("title") === "Clear" ||
                                 node.getAttribute("aria-label") === "Clear")) {
                                console.log("[Study] Found dynamically added trash icon:", node);
                                node.remove();
                                foundNewIcons = true;
                            }
                            
                            if (node.querySelectorAll) {
                                const selectors = [
                                    ".icon-button-wrapper.top-panel.hide-top-corner",
                                    ".icon-button-wrapper.top-panel",
                                    "button[title='Clear']",
                                    "button[aria-label='Clear']"
                                ];
                                
                                selectors.forEach(selector => {
                                    const elements = node.querySelectorAll(selector);
                                    if (elements.length > 0) {
                                        console.log(`[Study] Found ${elements.length} trash icons inside new element:`, selector);
                                        elements.forEach(el => el.remove());
                                        foundNewIcons = true;
                                    }
                                });
                            }
                        }
                    });
                }
            }
            
            if (foundNewIcons) {
                console.log("[Study] Removed dynamically added trash icons");
            }
        });
        
        iconObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log("[Study] Set up observer to remove dynamically added trash icons");
        
        setTimeout(() => {
            iconObserver.disconnect();
            console.log("[Study] Disconnected trash icon removal observer after timeout");
        }, 120000);
        
    } catch (error) {
        console.error("[Study] Error setting up icon removal observer:", error);
    }
}

function updateProgressBar(stage) {
    const footerComponent = document.querySelector('footer-component');
    if (!footerComponent) {
        console.warn("[Study] Footer component not found, can't update progress");
        return;
    }
    
    const progress = 40 + ((stage - 1) * 10);
    console.log(`[Study] Updating progress bar to ${progress}% for scenario stage ${stage}`);
    
    footerComponent.setAttribute('progress', progress.toString());
}

function setupNextScenarioButton() {
    const nextScenarioBtn = document.querySelector("#next-scenario-btn");
    if (!nextScenarioBtn) {
        console.warn("[Study] Next scenario button not found");
        return;
    }

    console.log("[Study] Setting up next scenario button");
    console.log("[Study] Button text:", nextScenarioBtn.textContent.trim());
    
    let isProcessing = false;
    
    nextScenarioBtn.addEventListener("click", async () => {
        if (isProcessing) {
            console.log("[Study] Button click ignored - already processing");
            return;
        }
        
        isProcessing = true;
        nextScenarioBtn.setAttribute('disabled', 'disabled');

        const scenarioHeaderCard = document.querySelector(".scenario-header-card");
        if (scenarioHeaderCard) {
            scenarioHeaderCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        try {
            console.log("[Study] Next scenario button clicked");
            
            await updateScenarioStage(scenario_stage + 1);
        
        console.log("[Study] Button text:", nextScenarioBtn.textContent.trim());
            console.log("[Study] Button classes:", nextScenarioBtn.className);
            
            const isStudyCompleted = nextScenarioBtn.classList.contains("study-completed-btn");
            console.log("[Study] Is study completed? (class-based detection)", isStudyCompleted);
            
            if (!isStudyCompleted && nextScenarioBtn.textContent.trim().includes("Weiter zum Fragebogen")) {
                console.log("[Study] Study completion detected by button text (fallback method)");
                const isStudyCompletedByText = true;
                handleStudyCompletion(isStudyCompletedByText);
            } else if (isStudyCompleted) {
                handleStudyCompletion(isStudyCompleted);
            }
        } catch (error) {
            console.error("[Study] Error processing next scenario:", error);
            errorModal.show(error_texts.error_texts.general_error);
        } finally {
            setTimeout(() => {
                isProcessing = false;
                nextScenarioBtn.removeAttribute('disabled');
            }, 1000);
        }
    });
}

async function handleStudyCompletion(isStudyCompleted) {
        if (isStudyCompleted) {
          console.log("[Study] Study completed, setting cookie and redirecting");
          Cookies.set("gradio-main-study-completed", "true", { path: '/' });
          
          console.log("[Study] Cookie set:", Cookies.get("gradio-main-study-completed"));

          try {
            const user = auth.currentUser;
            if (!user) {
              console.error("[Post-Study] Error: No authenticated user found.");
              errorModal.show(error_texts.error_texts.general.no_user_found);
              return false;
            }
      
            const studyToken = user.displayName;
            if (!studyToken) {
              console.error("[Post-Study] Error: No study token found.");
              errorModal.show(error_texts.error_texts.general.no_study_token);
              return false;
            }
      
            const userDocRef = doc(db, "users", studyToken);
            await updateDoc(userDocRef, {
              lastStage: "study",
              lastActiveAt: serverTimestamp(),
                studyStatus: "completed",
                "mainStudy.gradio_app_finished": true,
                "mainStudy.last_scenario_stage": scenario_stage
            });

            const response = await fetch("/api/submit-study", {
              method: "POST"
            });

            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log("[Study] Study data submitted successfully:", result);
            
            setTimeout(() => {
                try {
                    console.log("[Study] Attempting to navigate to post-study");
                    window.location.href = "/post-study";
                } catch (error) {
                    console.error("[Study] Navigation error:", error);
                }
            }, 100);
          } catch (error) {
            console.error("[Study] Error:", error);
            errorModal.show(error_texts.error_texts.general_error);
          }
      }
}
