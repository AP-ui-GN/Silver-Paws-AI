/**
 * Bundled only by upload-cleanup.test.ts. The API source imports extensionless
 * paths, which esbuild resolves and Node's type stripper does not.
 */

import express from "express";

import analyzeRouter from "../src/routes/analyze.ts";

const app = express();
app.use("/api", analyzeRouter);

export default app;
