import { onRequest } from "firebase-functions/v2/https";
import { initializeApp } from "firebase-admin/app";
import { getStorage } from "firebase-admin/storage";

// Force the Admin SDK to use the local emulator if running locally
if (process.env.FUNCTIONS_EMULATOR === "true") {
  process.env.FIREBASE_STORAGE_EMULATOR_HOST = "127.0.0.1:9199";
}

initializeApp({
  projectId: "stats-agent-4a718",
});

export const getFile = onRequest({ cors: true }, async (req, res) => {
  try {
    const apiKey = req.headers["x-api-key"];
    // Basic authentication for a single-team deployment
    if (apiKey !== process.env.BACKEND_SECRET_KEY) {
      res.status(401).send("Unauthorized");
      return;
    }

    let objectPath = req.query.path || req.body.path;

    if (!objectPath) {
      res.status(400).send("Missing 'path' parameter");
      return;
    }

    if (typeof objectPath === 'string') {
      objectPath = decodeURIComponent(objectPath);
    }

    // Explicitly use the modern Firebase bucket name used by the Flutter client.
    // The Admin SDK often incorrectly defaults to [project-id].appspot.com in the local emulator.
    const bucket = getStorage().bucket('stats-agent-4a718.firebasestorage.app');
    const file = bucket.file(objectPath as string);

    const [exists] = await file.exists();

    if (!exists) {
      res.status(404).send("File not found in bucket stats-agent-4a718.firebasestorage.app");
      return;
    }

    const [metadata] = await file.getMetadata();

    res.setHeader("Content-Type", metadata.contentType || "application/octet-stream");
    res.setHeader("Content-Disposition", `inline; filename="${metadata.name}"`);

    // Stream the file bytes directly. This is the most robust method for local 
    // emulators, avoiding the complexities and bugs of Signed URLs locally.
    file.createReadStream().pipe(res);

  } catch (error) {
    console.error("Error retrieving file:", error);
    res.status(500).send("Error retrieving file");
  }
});