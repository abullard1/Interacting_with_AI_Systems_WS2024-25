/**
 * Token Expired Page Controller
 */

import Cookies from "js-cookie";
import { setButtonLoading } from './loading-button-change.js';

console.log("[Token Expired Page] token-expired.js loaded.");

document.addEventListener("DOMContentLoaded", function() {
  console.log("[Token Expired] DOM fully loaded and parsed");
  
  clearStudyCookies();
  console.log("[Token Expired] Proactively cleared cookies on page load");
  
  const restartButton = document.getElementById("restart-btn");
  
  restartButton.addEventListener("click", function() {
    console.log("[Token Expired] Restart button clicked, redirecting to start page");
    
    setButtonLoading(true, false, "restart-btn", "Zur Startseite");
    
    clearStudyCookies();
    
    setTimeout(() => {
      window.location.href = "/";
    }, 500);
  });
  
  function clearStudyCookies() {
    console.log("[Token Expired] Clearing study session cookies");
    
    Cookies.remove("study_token", { 
      path: "/", 
      secure: true, 
      sameSite: "None" 
    });
    
    const regularCookieOptions = { path: "/" };
    Cookies.remove("consent-given", regularCookieOptions);
    Cookies.remove("pre-study-completed", regularCookieOptions);
    Cookies.remove("token-page-completed", regularCookieOptions);
    Cookies.remove("study-explanation-completed", regularCookieOptions);
    Cookies.remove("gradio-main-study-completed", regularCookieOptions);
    Cookies.remove("post-study-completed", regularCookieOptions);
    
    console.log("[Token Expired] Study session cookies cleared while preserving completion status");
  }
  
  setTimeout(() => {
    const navbar = document.querySelector('navbar-component');
    const footer = document.querySelector('footer-component');
    
    if (!navbar || !footer) {
      console.error("[Token Expired] Components not loaded properly");
    } else {
      console.log("[Token Expired] All components loaded successfully");
    }
  }, 1000);
}); 