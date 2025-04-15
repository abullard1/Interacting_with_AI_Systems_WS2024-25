// Gets the average, median, min and max age of participants in the study
const simpleStatistics = require('simple-statistics');
const admin = require('firebase-admin');
const serviceAccount = require('../../../firebase_adminsdk_key.json');


admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  projectId: 'interacting-with-ai-systems'
});

const usersCollection = admin.firestore().collection('users');

async function getParticipantAges() {
  const snapshot = await usersCollection.get();
  const participants = snapshot.docs.map((doc) => doc.data());
  const agesRaw = participants.map((participant) => participant.preStudyQuestionnaire?.demographics?.age);
  const ages = agesRaw.filter(age => typeof age === 'number' && !isNaN(age));

  const nullAgeCount = agesRaw.length - ages.length;
  console.log(`Number of participants with missing or invalid age data: ${nullAgeCount}`);

  if (ages.length === 0) {
    console.log("No valid age data found for any participant.");
    return;
  }

  // Age frequency analysis
  const ageBrackets = {
    '18-24': 0,
    '25-34': 0,
    '35-44': 0,
    '45-54': 0,
    '55-64': 0,
    '65+': 0,
    'Other': 0
  };

  ages.forEach(age => {
    if (age >= 18 && age <= 24) ageBrackets['18-24']++;
    else if (age >= 25 && age <= 34) ageBrackets['25-34']++;
    else if (age >= 35 && age <= 44) ageBrackets['35-44']++;
    else if (age >= 45 && age <= 54) ageBrackets['45-54']++;
    else if (age >= 55 && age <= 64) ageBrackets['55-64']++;
    else if (age >= 65) ageBrackets['65+']++;
    else ageBrackets['Other']++;
  });

  let largestBracket = '';
  let maxCount = 0;
  for (const bracket in ageBrackets) {
    if (ageBrackets[bracket] > maxCount) {
      maxCount = ageBrackets[bracket];
      largestBracket = bracket;
    }
  }

  console.log(`Largest age bracket: ${largestBracket} with ${maxCount} participants`);
  console.log("Age bracket distribution:", ageBrackets);

  const meanAge = simpleStatistics.mean(ages);
  const medianAge = simpleStatistics.median(ages);
  const modeAge = simpleStatistics.mode(ages);
  const minAge = simpleStatistics.min(ages);
  const maxAge = simpleStatistics.max(ages);
  console.log(`Mean age: ${meanAge}`);
  console.log(`Median age: ${medianAge}`);
  console.log(`Mode age: ${modeAge}`);
  console.log(`Min age: ${minAge}`);
  console.log(`Max age: ${maxAge}`);
}

getParticipantAges();
