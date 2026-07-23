// Extracts specific timing metrics (submit_vs_loading, loading_to_response) 
// from Firestore for each participant and stage, saving to CSV.

const admin = require('firebase-admin');
const { Parser } = require('json2csv');
const fs = require('fs');
const path = require('path');

const serviceAccount = require('../../../firebase_adminsdk_key.json'); 
const projectId = 'interacting-with-ai-systems'; 
const outputCsvFile = path.join(__dirname, '../extracted_data/timing_data.csv');
const MAX_STAGES = 4;

const outputDir = path.dirname(outputCsvFile);
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
    console.log(`Created output directory: ${outputDir}`);
}

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  projectId: projectId 
});

const db = admin.firestore();
const usersCollection = db.collection('users');

async function extractTimingData() {
  console.log("Fetching user data for timing metrics...");
  const snapshot = await usersCollection.get();
  
  if (snapshot.empty) {
    console.log('No user documents found.');
    return;
  }  

  console.log(`Found ${snapshot.docs.length} user documents. Processing...`);
  
  let processedUsersCount = 0;
  const allTimingData = []; // Array to store rows for CSV

  snapshot.docs.forEach((doc) => {
    const participantId = doc.id;
    const userData = doc.data();
    
    const submitVsLoadingData = userData?.mainStudy?.submit_vs_loading_appear_time_difference;
    const loadingToResponseData = userData?.mainStudy?.loading_to_response_time_difference;

    let userHasAnyStageData = false;

    for (let stage = 1; stage <= MAX_STAGES; stage++) {
        const stageKey = `stage_${stage}`;

        let submitVsLoadingMs = submitVsLoadingData?.[stageKey] ?? null;
        let loadingToResponseMs = loadingToResponseData?.[stageKey] ?? null;

        if (submitVsLoadingMs !== null && typeof submitVsLoadingMs !== 'number') {
            console.warn(`User ${participantId}, Stage ${stage}: Invalid submit_vs_loading value (${submitVsLoadingMs}). Setting to null.`);
            submitVsLoadingMs = null;
        }
        if (loadingToResponseMs !== null && typeof loadingToResponseMs !== 'number') {
             console.warn(`User ${participantId}, Stage ${stage}: Invalid loading_to_response value (${loadingToResponseMs}). Setting to null.`);
            loadingToResponseMs = null;
        }

        if (submitVsLoadingMs !== null || loadingToResponseMs !== null) {
            allTimingData.push({
                participant_id: participantId,
                stage: stage,
                submit_vs_loading_ms: submitVsLoadingMs,
                loading_to_response_ms: loadingToResponseMs
            });
            userHasAnyStageData = true;
        }
    }

    if (userHasAnyStageData) {
        processedUsersCount++;
    }
  });

  console.log(`\nFinished processing. Found stage timing data for ${processedUsersCount} users.`);

  if (allTimingData.length > 0) {
    try {
      const fields = ['participant_id', 'stage', 'submit_vs_loading_ms', 'loading_to_response_ms'];
      const opts = { fields };
      const parser = new Parser(opts);
      const csv = parser.parse(allTimingData);

      fs.writeFileSync(outputCsvFile, csv, 'utf8');
      console.log(`\nTiming data successfully saved to: ${outputCsvFile}`);

    } catch (err) {
      console.error("\nError writing CSV file:", err);
    }
  } else {
    console.log("\nNo valid stage timing data found across any users to save.");
  }
}

async function checkAndInstallDeps() {
    try {
        require.resolve('firebase-admin');
        require.resolve('json2csv');
        console.log("Dependencies found.");
        await extractTimingData();
    } catch (e) {
        console.log("Required dependencies (firebase-admin, json2csv) not found. Attempting to install...");
        const { exec } = require('child_process');
        exec('npm install firebase-admin json2csv', { cwd: path.dirname(__filename) }, (error, stdout, stderr) => { // Run npm install in script's dir
            if (error) {
                console.error(`Error installing dependencies: ${error}`);
                console.error("Please install 'firebase-admin' and 'json2csv' manually using npm or yarn.");
                return;
            }
            console.log(`Installation output: ${stdout}`);
            if (stderr) {
                console.error(`Installation stderr: ${stderr}`);
            }
            console.log("Installation complete. Please re-run the script.");
        });
    }
}

checkAndInstallDeps().catch(error => {
  console.error("Error during script execution:", error);
}); 