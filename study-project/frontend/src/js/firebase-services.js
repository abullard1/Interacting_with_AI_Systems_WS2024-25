/**
 * Firebase Services
 */

import { app } from "./initialize-firebase.js";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const auth = getAuth(app);
const db = getFirestore(app);

export { auth, db };