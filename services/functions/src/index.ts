import { onRequest } from "firebase-functions/v2/https";
import { initializeApp } from "firebase-admin/app";
import { getStorage } from "firebase-admin/storage";

initializeApp();

export const getFile = onRequest({ cors: true }, async (req, res) => {
  try {
    const apiKey = req.headers["x-api-key"];
    // Basic authentication for a single-team deployment
    if (apiKey !== "secret-agent-key-123") {
      res.status(401).send("Unauthorized");
      return;
    }

    const objectPath = req.query.path || req.body.path;

    if (!objectPath) {
      res.status(400).send("Missing 'path' parameter");
      return;
    }

    const bucket = getStorage().bucket();
    const file = bucket.file(objectPath);

    const [exists] = await file.exists();

    if (!exists) {
      res.status(404).send("File not found");
      return;
    }

    // Generate a secure, temporary Signed URL
    const [url] = await file.getSignedUrl({
      action: "read",
      expires: Date.now() + 1000 * 60 * 60, // 1 hour
    });

    res.status(200).json({ url });

  } catch (error) {
    console.error(error);
    res.status(500).send("Error generating signed URL");
  }
});