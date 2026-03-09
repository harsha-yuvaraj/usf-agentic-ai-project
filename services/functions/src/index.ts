import { onRequest } from "firebase-functions/v2/https";
import { initializeApp } from "firebase-admin/app";
import { getStorage } from "firebase-admin/storage";

initializeApp();

export const getFile = onRequest(async (req, res) => {
  try {
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

    const [metadata] = await file.getMetadata();

    res.setHeader("Content-Type", metadata.contentType || "application/octet-stream");
    res.setHeader("Content-Disposition", `inline; filename="${metadata.name}"`);

    file.createReadStream().pipe(res);

  } catch (error) {
    console.error(error);
    res.status(500).send("Error retrieving file");
  }
});