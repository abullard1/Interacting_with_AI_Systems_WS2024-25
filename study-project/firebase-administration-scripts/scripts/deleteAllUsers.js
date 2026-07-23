// Deletes all users from the Firebase Auth database and Firestore database (users collection)
const admin = require('firebase-admin');
const serviceAccount = require('../../../firebase_adminsdk_key.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  projectId: 'interacting-with-ai-systems'
});

// Function to delete all documents in the 'users' collection in Firestore
async function deleteAllFirestoreUsers() {
  try {
    console.log('\n=================================');
    console.log('FIRESTORE USER DOCUMENT DELETION');
    console.log('=================================\n');
    console.log('Deleting all Firestore user documents...');
    
    // Get all documents from the 'users' collection
    const usersSnapshot = await admin.firestore().collection('users').get();
    
    let deleteCount = 0;
    let errorCount = 0;
    let totalDocuments = 0;
    
    if (usersSnapshot.empty) {
      console.log('No Firestore user documents found to delete.');
    } else {
      totalDocuments = usersSnapshot.size;
      console.log(`Found ${totalDocuments} Firestore user documents to delete.`);
      
      // Delete each document
      for (const doc of usersSnapshot.docs) {
        try {
          console.log(`Deleting Firestore user document: ${doc.id}`);
          await doc.ref.delete();
          console.log(`Deleted Firestore user document: ${doc.id}`);
          deleteCount++;
        } catch (error) {
          console.error(`Error deleting Firestore user document: ${doc.id}`, error);
          errorCount++;
        }
      }
    }
    
    console.log('\n=====================================');
    console.log('FIRESTORE USER DOCUMENTS DELETION SUMMARY');
    console.log('=====================================');
    console.log(`Total Firestore documents found: ${totalDocuments}`);
    console.log(`Successfully deleted: ${deleteCount}`);
    console.log(`Failed to delete: ${errorCount}`);
    console.log('=====================================\n');
    
    return deleteCount;
  } catch (error) {
    console.error('Error deleting Firestore users:', error);
    return 0;
  }
}

async function deleteAllUsers() {
  try {
    console.log('\n================================');
    console.log('FIREBASE AUTH USER DELETION');
    console.log('================================\n');
    console.log('Deleting all Auth users...');
    const users = [];
    let successCount = 0;
    let errorCount = 0;
    let pageToken;

    // Loop through all users using pagination
    do {
      try {
        const listUsersResult = await admin.auth().listUsers(1000, pageToken);
        
        if (listUsersResult.users.length === 0) {
          console.log('No Auth users found to delete.');
          break;
        }
        
        for (const userRecord of listUsersResult.users) {
          users.push(userRecord);
          let userDeleted = true;

          try {
            await admin.auth().deleteUser(userRecord.uid);
            console.log(`Deleted Auth User: ${userRecord.uid}`);
          } catch (error) {
            console.error(`Error deleting Auth User: ${userRecord.uid}`, error);
            userDeleted = false;
          }

          try {
            console.log(`Deleting Firestore User: ${userRecord.uid}`);
            await admin.firestore().collection('users').doc(userRecord.uid).delete();
            console.log(`Deleted Firestore User: ${userRecord.uid}`);
          } catch (error) {
            console.error(`Error deleting Firestore User: ${userRecord.uid}`, error);
            userDeleted = false;
          }

          if (userDeleted) {
            successCount++;
          } else {
            errorCount++;
          }
        }
        
        // Get the page token for the next page of users (if available)
        pageToken = listUsersResult.pageToken;
        
      } catch (error) {
        console.error('Error listing users:', error);
        break;
      }
    } while (pageToken);

    console.log('\n===================================');
    console.log('FIREBASE AUTH USERS DELETION SUMMARY');
    console.log('===================================');
    console.log(`Total Auth users processed: ${users.length}`);
    console.log(`Successfully deleted: ${successCount}`);
    console.log(`Failed to delete: ${errorCount}`);
    console.log('===================================\n');
  } catch (error) {
    console.error('Error deleting all users:', error);
  }
}

deleteAllUsers();
deleteAllFirestoreUsers();
