import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { httpsOnlyApplies, requestIsHttps, trustProxyEnabled } from "./lib/hosting";
import { logger } from "./lib/logger";

const app: Express = express();

if (trustProxyEnabled()) {
  app.set("trust proxy", 1);
}

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());
app.use((req, res, next) => {
  if (!httpsOnlyApplies(process.env["NODE_ENV"], req.path)) {
    next();
    return;
  }
  if (requestIsHttps(req.secure, req.header("x-forwarded-proto"), trustProxyEnabled())) {
    next();
    return;
  }
  res.status(400).json({
    ok: false,
    error: "Open this server with https://.",
  });
});
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

export default app;
