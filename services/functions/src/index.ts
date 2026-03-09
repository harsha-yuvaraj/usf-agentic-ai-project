import functions from 'firebase-functions';
import admin from 'firebase-admin';

// Initialize Firebase Admin if not already initialized
if (!admin.apps.length) {
  admin.initializeApp();
}

/**
 * Firebase Cloud Function to retrieve data from Firebase Storage
 * 
 * Usage:
 * HTTP GET: https://your-region-your-project.cloudfunctions.net/getStorageData?path=folder/file.txt
 * HTTP POST: { "path": "folder/file.txt" }
 * 
 * Optional parameters:
 * - download: Set to 'true' to force download instead of inline display
 * - signedUrl: Set to 'true' to return a signed URL instead of the file content
 */
exports.getStorageData = functions.https.onRequest(async (req, res) => {
  // Enable CORS
  res.set('Access-Control-Allow-Origin', '*');
  
  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'GET, POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.set('Access-Control-Max-Age', '3600');
    res.status(204).send('');
    return;
  }

  try {
    // Get the file path from query params or request body
    const filePath = req.query.path || req.body?.path;
    
    if (!filePath) {
      res.status(400).json({ 
        error: 'Missing required parameter: path' 
      });
      return;
    }

    // Get reference to the storage bucket
    const bucket = admin.storage().bucket();
    const file = bucket.file(filePath);

    // Check if file exists
    const [exists] = await file.exists();
    if (!exists) {
      res.status(404).json({ 
        error: 'File not found',
        path: filePath 
      });
      return;
    }

    // Get file metadata
    const [metadata] = await file.getMetadata();


    // Download and return the file content
    const [fileContents] = await file.download();

    // Set appropriate headers
    res.set('Content-Type', metadata.contentType || 'application/octet-stream');
    res.set('Content-Length', (metadata.size ?? 0).toString());
    
    // Force download or inline display
    if (req.query.download === 'true' || req.body?.download === true) {
      res.set('Content-Disposition', `attachment; filename="${metadata.name}"`);
    } else {
      res.set('Content-Disposition', `inline; filename="${metadata.name}"`);
    }

    // Return the file content
    res.status(200).send(fileContents);

  } catch (error) {
    console.error('Error retrieving file from Storage:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error 
    });
  }
});

