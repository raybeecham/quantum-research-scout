import { z } from "zod";
import { AppEnv, allowed, digest, equal, fail, hash, randomToken, upstream } from "./support";

const cookieName = "__Host-scout-oauth";
const cookie = (value: string, age: number) =>
  `${cookieName}=${value}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=${age}`;
export async function startLogin(request: Request, env: AppEnv) {
  // Browser challenge binds the eventual session to the initiating tab, including
  // cases where an attacker sends someone a link to a separate authorization flow.
  const challenge = new URL(request.url).searchParams.get("challenge") || "";
  if (!/^[a-f0-9]{64}$/.test(challenge)) fail(400, "auth", "Start sign-in from the research desk.");
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET || !env.ALLOWED_GITHUB_IDS.trim())
    fail(503, "setup", "GitHub sign-in has not been configured by the operator.");
  const state = randomToken(),
    verifier = randomToken();
  await env.AUTH.getByName("oauth:" + (await hash(state))).create(
    { kind: "oauth", verifier, challenge },
    600000,
  );
  const pkce = btoa(String.fromCharCode(...new Uint8Array(await digest(verifier))))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  const url = new URL("https://github.com/login/oauth/authorize");
  url.search = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    redirect_uri: env.BACKEND_ORIGIN + "/auth/callback",
    scope: "",
    state,
    code_challenge: pkce,
    code_challenge_method: "S256",
    allow_signup: "false",
  }).toString();
  return new Response(null, {
    status: 302,
    headers: { Location: url.href, "Set-Cookie": cookie(state, 600) },
  });
}
export async function finishLogin(request: Request, env: AppEnv) {
  const url = new URL(request.url),
    state = url.searchParams.get("state") || "",
    code = url.searchParams.get("code") || "";
  const supplied =
    request.headers
      .get("Cookie")
      ?.split(";")
      .map(s => s.trim())
      .find(s => s.startsWith(cookieName + "="))
      ?.slice(cookieName.length + 1) || "";
  if (!/^[a-f0-9]{64}$/.test(state) || !(await equal(state, supplied)))
    fail(
      403,
      "auth",
      "Sign-in expired or could not be verified. Start again from the research desk.",
    );
  const flow = await env.AUTH.getByName("oauth:" + (await hash(state))).read(true);
  if (!flow || flow.kind !== "oauth" || !code || code.length > 256)
    fail(403, "auth", "Sign-in expired or was cancelled. Start again from the research desk.");
  const tokenPayload = await upstream(
    "https://github.com/login/oauth/access_token",
    {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: env.GITHUB_CLIENT_ID,
        client_secret: env.GITHUB_CLIENT_SECRET,
        code,
        redirect_uri: env.BACKEND_ORIGIN + "/auth/callback",
        code_verifier: flow.verifier,
      }),
    },
    32000,
    15000,
  );
  const parsed = z
    .object({ access_token: z.string().min(1).max(1000), token_type: z.literal("bearer") })
    .safeParse(tokenPayload);
  if (!parsed.success)
    fail(403, "auth", "GitHub sign-in could not be completed. Please start again.");
  const githubToken = parsed.data!.access_token;
  const profile = z
    .object({ id: z.number().int().positive(), login: z.string().regex(/^[a-zA-Z0-9-]{1,39}$/) })
    .parse(
      await upstream(
        "https://api.github.com/user",
        {
          headers: {
            Authorization: `Bearer ${githubToken}`,
            Accept: "application/vnd.github+json",
            "User-Agent": "Quantum-Scout-Lab",
            "X-GitHub-Api-Version": "2022-11-28",
          },
        },
        64000,
        15000,
      ),
    );
  // GitHub's access token is never stored, returned to the browser, or used for repo access.
  const id = String(profile.id);
  if (!allowed(env, id))
    fail(
      403,
      "not_invited",
      "This research lab is invite-only. Your GitHub account is not on the operator's allowlist.",
    );
  const session = randomToken();
  await env.AUTH.getByName("session:" + (await hash(session))).create(
    { kind: "session", id, login: profile.login },
    3600000,
  );
  const nonce = randomToken();
  const payload = JSON.stringify({
    type: "scout-lab-session",
    token: session,
    challenge: flow.challenge,
  }).replace(/</g, "\\u003c");
  return new Response(
    `<!doctype html><html lang="en"><meta charset="utf-8"><title>Scout sign-in</title><p>Signed in. Return to your research desk. You can close this window.</p><script nonce="${nonce}">if(window.opener){window.opener.postMessage(${payload},${JSON.stringify(env.PUBLIC_ORIGIN)});window.close();}</script></html>`,
    {
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Set-Cookie": cookie("", 0),
        "Content-Security-Policy": `default-src 'none'; script-src 'nonce-${nonce}'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'`,
      },
    },
  );
}
export async function authenticate(request: Request, env: AppEnv) {
  const token = /^Bearer ([a-f0-9]{64})$/.exec(request.headers.get("Authorization") || "")?.[1];
  if (!token) return fail(401, "sign_in", "Sign in with GitHub to use the hosted lab.");
  const record = env.AUTH.getByName("session:" + (await hash(token)));
  const user = await record.read();
  if (!user || user.kind !== "session" || !allowed(env, user.id))
    return fail(401, "sign_in", "Your session expired or access changed. Sign in again.");
  return { user, record };
}
