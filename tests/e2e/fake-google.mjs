// A stand-in Google for end-to-end tests. The API reaches it through
// TAZKO_GOOGLE_URL; production refuses that setting. It speaks the part of
// OpenID Connect the API uses: /authorize shows an account chooser, /token
// turns a code into an RS256 ID token after checking the PKCE verifier, and
// /certs serves the public key. Node built-ins only.
//
//   node tests/e2e/fake-google.mjs        (port 8792, or FAKE_GOOGLE_PORT)

import {
  createHash,
  generateKeyPairSync,
  randomBytes,
  sign,
} from "node:crypto";
import { createServer } from "node:http";

const PORT = Number(process.env.FAKE_GOOGLE_PORT ?? 8792);
const BASE = `http://127.0.0.1:${PORT}`;
// Test values, also in playwright.config.ts. Not secrets.
export const CLIENT_ID = "e2e-client";
export const CLIENT_SECRET = "e2e-secret";
const PERSONAL = new Set(["gmail.com", "googlemail.com"]);

const { publicKey, privateKey } = generateKeyPairSync("rsa", {
  modulusLength: 2048,
});
const jwk = {
  ...publicKey.export({ format: "jwk" }),
  kid: "e2e-1",
  alg: "RS256",
  use: "sig",
};
/** code -> what the account chooser was asked and answered; each code works once. */
const codes = new Map();

const b64url = (data) => Buffer.from(data).toString("base64url");
const escape = (text) =>
  String(text).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );

function idToken({ email, name, nonce }) {
  const now = Math.floor(Date.now() / 1000);
  const domain = email.split("@")[1] ?? "";
  const claims = {
    iss: BASE,
    aud: CLIENT_ID,
    // The same account always gets the same sub, as with Google.
    sub: `e2e-${createHash("sha256").update(email).digest("hex").slice(0, 20)}`,
    email,
    email_verified: true,
    name,
    iat: now,
    exp: now + 600,
    nonce,
    // Workspace accounts carry hd; personal Gmail accounts do not.
    ...(PERSONAL.has(domain) ? {} : { hd: domain }),
  };
  const head = b64url(
    JSON.stringify({ alg: "RS256", kid: jwk.kid, typ: "JWT" }),
  );
  const body = b64url(JSON.stringify(claims));
  const signature = sign(
    "RSA-SHA256",
    Buffer.from(`${head}.${body}`),
    privateKey,
  );
  return `${head}.${body}.${b64url(signature)}`;
}

function send(res, status, body, type = "application/json") {
  res.writeHead(status, { "content-type": type, "cache-control": "no-store" });
  res.end(type === "application/json" ? JSON.stringify(body) : body);
}

async function form(req) {
  let text = "";
  for await (const chunk of req) text += chunk;
  return Object.fromEntries(new URLSearchParams(text));
}

const ASKED = ["client_id", "redirect_uri", "state", "nonce", "code_challenge"];

function chooser(params) {
  const hidden = ASKED.map(
    (k) => `<input type="hidden" name="${k}" value="${escape(params.get(k))}">`,
  ).join("");
  return `<!doctype html><meta charset="utf-8"><title>Choose an account</title>
<h1>Choose an account</h1><p>Stand-in Google for e2e tests.</p>
<form method="post" action="/authorize">${hidden}
<label>Email <input name="email" type="email" required></label>
<label>Name <input name="name"></label>
<button type="submit">Continue</button></form>`;
}

async function authorize(req, res, url) {
  if (req.method === "GET") {
    const p = url.searchParams;
    const missing = ASKED.filter((k) => !p.get(k));
    if (p.get("client_id") !== CLIENT_ID || p.get("response_type") !== "code") {
      return send(res, 400, "unknown client or response type", "text/plain");
    }
    if (missing.length || p.get("code_challenge_method") !== "S256") {
      return send(
        res,
        400,
        `missing ${missing.join(", ") || "S256"}`,
        "text/plain",
      );
    }
    return send(res, 200, chooser(p), "text/html; charset=utf-8");
  }
  const chosen = await form(req);
  let back;
  try {
    back = new URL(chosen.redirect_uri);
  } catch {
    return send(res, 400, "missing redirect_uri", "text/plain");
  }
  if (chosen.client_id !== CLIENT_ID) {
    return send(res, 400, "unknown client", "text/plain");
  }
  const code = b64url(randomBytes(24));
  codes.set(code, chosen);
  back.searchParams.set("code", code);
  back.searchParams.set("state", chosen.state);
  res.writeHead(302, { location: back.toString() });
  res.end();
}

async function token(req, res) {
  const f = await form(req);
  const asked = codes.get(f.code);
  codes.delete(f.code);
  const verifier = createHash("sha256")
    .update(f.code_verifier ?? "")
    .digest("base64url");
  if (
    !asked ||
    f.grant_type !== "authorization_code" ||
    f.client_id !== CLIENT_ID ||
    f.client_secret !== CLIENT_SECRET ||
    f.redirect_uri !== asked.redirect_uri ||
    verifier !== asked.code_challenge
  ) {
    return send(res, 400, { error: "invalid_grant" });
  }
  const email = asked.email.trim().toLowerCase();
  const name = asked.name?.trim() || email.split("@")[0];
  send(res, 200, {
    id_token: idToken({ email, name, nonce: asked.nonce }),
    access_token: "unused",
    token_type: "Bearer",
    expires_in: 600,
  });
}

createServer((req, res) => {
  const url = new URL(req.url ?? "/", BASE);
  const route = `${req.method} ${url.pathname}`;
  if (url.pathname === "/authorize") return void authorize(req, res, url);
  if (route === "POST /token") return void token(req, res);
  if (route === "GET /certs") return send(res, 200, { keys: [jwk] });
  if (route === "GET /health") return send(res, 200, { ok: true });
  send(res, 404, { error: "not_found" });
}).listen(PORT, "127.0.0.1", () => console.log(`fake Google on ${BASE}`));
