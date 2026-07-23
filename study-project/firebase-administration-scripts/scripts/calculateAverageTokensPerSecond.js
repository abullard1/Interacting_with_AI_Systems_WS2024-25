// Calculates the average tokens per second (TPS) across all completed 
// experimental conditions for each participant.

const simpleStatistics = require('simple-statistics');
const admin = require('firebase-admin');
const serviceAccount = require('../../../firebase_adminsdk_key.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  projectId: 'interacting-with-ai-systems'
});

const db = admin.firestore();
const usersCollection = db.collection('users');

async function calculateAverageTpsPerUser() {
  console.log("Fetching user data...");
  const snapshot = await usersCollection.get();
  
  if (snapshot.empty) {
    console.log('No matching user documents found.');
    return;
  }  

  console.log(`Found ${snapshot.docs.length} user documents. Processing...`);
  
  const conditionKeys = ['fast_easy', 'fast_hard', 'slow_easy', 'slow_hard'];
  let processedUsers = 0;
  const allTpsValues = []; // Array to store TPS values from all users

  snapshot.docs.forEach((doc) => {
    const userId = doc.id;
    const userData = doc.data();
    const userTpsValues = [];

    const scenariosData = userData?.mainStudy?.scenarios;

    if (scenariosData) {
      conditionKeys.forEach(conditionKey => {
        const tps = scenariosData[conditionKey]?.tokens_per_second;
        if (typeof tps === 'number' && !isNaN(tps)) {
          userTpsValues.push(tps);
        }
      });
    }

    if (userTpsValues.length > 0) {
      const averageTps = simpleStatistics.mean(userTpsValues);
      console.log(`User: ${userId}, Average TPS across ${userTpsValues.length} condition(s): ${averageTps.toFixed(2)}`);
      allTpsValues.push(...userTpsValues); 
    } else {
      console.log(`User: ${userId}, No valid TPS data found in completed conditions.`);
    }
    processedUsers++;
  });

  console.log(`\nFinished processing ${processedUsers} users.`);

  if (allTpsValues.length > 0) {
    const overallAverageTps = simpleStatistics.mean(allTpsValues);
    console.log(`\nOverall Average TPS across all users and conditions (${allTpsValues.length} data points): ${overallAverageTps.toFixed(2)}`);
  } else {
    console.log("\nNo valid TPS data found across any users to calculate an overall average.");
  }
}

calculateAverageTpsPerUser().catch(error => {
  console.error("Error calculating average TPS:", error);
});