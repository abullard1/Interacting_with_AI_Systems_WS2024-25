/**
 * Firebase Configuration and Initialization
 */


import { initializeApp, getApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, setPersistence, browserLocalPersistence } from "firebase/auth";

console.log("[Firebase Initializer] Starting Firebase initialization.");

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

let app;
try {
  app = getApp();
  console.log("[Firebase Initializer] Existing Firebase instance found.");
} catch (error) {
  app = initializeApp(firebaseConfig);
  console.log("[Firebase Initializer] Firebase app initialized.");
}

try {
  const auth = getAuth(app);
  setPersistence(auth, browserLocalPersistence)
    .then(() => {
      console.log("[Firebase Initializer] Auth persistence set to LOCAL.");
    })
    .catch((error) => {
      console.error("[Firebase Initializer] Error setting persistence:", error);
    });
} catch (error) {
  console.error("[Firebase Initializer] Error with auth setup:", error);
}

let analytics;
try {
  analytics = getAnalytics(app);
  console.log("[Firebase Initializer] Firebase Analytics initialized.");
} catch (error) {
  console.error("[Firebase Initializer] Failed to initialize Analytics:", error);
}

export { app, analytics };
