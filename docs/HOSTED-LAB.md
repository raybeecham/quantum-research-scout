# Hosted research lab

This adds an invite-only Cloudflare Worker behind the existing GitHub Pages dashboard. It does **not** expose the Python loopback server. The checked-in configuration targets the Scout deployment and allows only its owner's numeric GitHub account ID. Credentials remain Cloudflare secrets, never repository files. For a new deployment or fork, set `LAB_ENABLED` to `false`, clear the client ID and allowlist, and follow the setup below with your own URLs and credentials. Building or pushing this repository alone does not deploy the backend.

## What is built

- GitHub OAuth authorization-code sign-in with PKCE, a Secure/HttpOnly/SameSite=Lax state cookie, single-use server state, and an initiating-tab challenge.
- An exact GitHub **numeric account ID** allowlist, checked at sign-in and on every API call. A renamed username does not grant another account access.
- One-hour opaque sessions. Only a hash identifies server-side session records; browser tokens live in memory, not URLs, cookies on GitHub Pages, localStorage, or exports. Reloading requires sign-in again. Sign-out revokes the session; removing an account ID blocks all its sessions immediately.
- Gemini draft + critique, explicit Groq backup, excerpt-only reading help, and Crossref/arXiv discovery. No automatic retry or provider switching. Source IDs and output schemas are validated.
- Atomic per-user and shared daily budgets, across both providers. Defaults: **10 AI call slots per user / 20 shared**, **20 searches per user / 100 shared**. Generation reserves two slots, reading help one, searches none. Reservations precede upstream calls; failed attempts count. UTC midnight reset. Within each daily budget, ten-second AI / four-second search cooldowns allow one in-flight request of each kind per user and at most two shared. Requests already running across midnight may overlap the next day's requests; accounting follows the reservation date.
- Bounded input/output streams, fixed upstream endpoints, exact-origin CORS, no public proxy, no credentials in browser assets. Only source excerpts explicitly selected by the user are sent; private notebook notes remain local.

The Cloudflare rate-limit binding is only an edge abuse throttle, not the accounting mechanism. Durable Objects enforce the actual budgets in one synchronous transaction per deployment/day. OAuth/session records are separately sharded and expire via alarms; daily counters expire after two days. No prompts, papers, notebook contents, or AI responses are persisted by this backend. Cloudflare storage recovery/retention policies can still apply. Providers and paper indexes have their own data policies. Do not submit sensitive or unpublished confidential research.

## Deploy once, then connect the page

Run from PowerShell:

```powershell
Set-Location F:\quantum-research-scout\hosted-lab
npm ci
npx wrangler login
npx wrangler whoami
npm run check
npm run lint
npm test
npm run dry-run
```

1. Check the Cloudflare account's plan and limits before deploying. No paid plan is required by the application design, but availability and billing are controlled by your Cloudflare and AI-provider accounts. These call limits are **not** an account-wide dollar cap or protection against all infrastructure abuse. Use separate provider projects/keys and provider-level spend controls where available. Do not enable billing solely for this pilot without deciding on a budget.
2. Deploy the **disabled** Worker with `npm run deploy`. Record its `https://quantum-scout-lab.<your-subdomain>.workers.dev` URL. Do not use a preview deployment URL.
3. In GitHub **Settings → Developer settings → OAuth Apps → New OAuth App**, register a dedicated app:
   - Name: `Quantum Research Scout Lab`
   - Homepage: `https://raybeecham.github.io/quantum-research-scout/`
   - Authorization callback: **the exact Worker URL plus `/auth/callback`**
   - No repository scopes are requested by the code. Do not reuse an app with broader existing grants.
4. Edit `hosted-lab/wrangler.jsonc`:
   - `BACKEND_ORIGIN`: the exact HTTPS Worker origin, without trailing slash.
   - `GITHUB_CLIENT_ID`: the OAuth application's public client ID.
   - `ALLOWED_GITHUB_IDS`: initially only your numeric GitHub user ID. Obtain it from `https://api.github.com/users/raybeecham`; verify the returned login. Add invited researchers later as comma-separated IDs, never `*`.
   - Keep `PUBLIC_ORIGIN` as `https://raybeecham.github.io`. CORS trusts this entire origin, so all other pages/scripts under the same origin must be trusted too.
   - Keep the conservative quotas, and set `LAB_ENABLED` to `true` only when setup is complete.
5. Store the three secrets interactively (values are never command-line arguments or repository files):

```powershell
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put GROQ_API_KEY
```

6. Run `npm run check`, `npm test`, `npm run dry-run`, then `npm run deploy`. This repository does not automatically deploy backend changes or upload local `.env.local` keys.
7. Set `api_origin` in `dashboard/lab-config.json` to the exact Worker origin. This is a **public URL, not a secret**. Do not add user-editable backend URLs, tokens or keys. Rebuild/publish GitHub Pages through the normal repository workflow.
8. Hard-refresh the public Question Lab. Click **Sign in with GitHub**, approve the dedicated app, and return to the research desk. Only allowlisted accounts can complete sign-in. Keep the popup open until it finishes. Notebook and question storage remains on GitHub Pages; nothing is migrated to the Worker.

The current local private server and its `.env.local` remain separate. Local previews never silently switch to the hosted backend. The hosted and local call budgets are separate, so use separate provider projects/keys if you need independent spending controls.

## Acceptance checks

1. Before sign-in, confirm AI and paper search are disabled and no provider request is made.
2. Sign in with the invited account. Confirm username, Gemini/Groq configuration, and call/search counts appear.
3. Generate once with Gemini after explicit consent: three revised candidates; usage increases by **two**, not one. Confirm a draft is not shown if critique fails.
4. Try Groq only after its separate consent: attribution says Groq and uses the same shared cap. No automatic fallback occurs.
5. Develop a question, click **Find papers**, open a source, and attach it. Search consumes one search reservation but no AI slots. Index outages produce warnings rather than a false “no prior work” conclusion.
6. Use the Notebook reading assistant after consent: one AI slot, excerpt-only context. Private notes are not included in the request body.
7. Sign out. New AI requests must fail; saved questions remain. Refreshing the page must require sign-in again. A copied stale/expired token must return 401.
8. An uninvited GitHub account must be denied. Remove an invited ID, redeploy, and verify its existing session is immediately rejected.
9. Temporarily lower the test deployment's daily cap to two. One generation uses it; switching to Groq or opening another tab must not bypass it. Restore the intended cap afterward. Do not clear production counters to test limits.
10. Check narrow/mobile layouts, popup-blocked feedback, server outage messaging, and disabled-provider controls. Backend unit tests mock providers and never spend real AI credits; live OAuth and real provider acceptance require the deployed account configuration.

## Operations and rollback

- Emergency pause: set `LAB_ENABLED` to `false` and redeploy. Authentication and workload endpoints fail closed; saved browser work is unaffected. Already-running upstream calls may finish.
- Revoke an account: remove its numeric ID and redeploy. Sessions are rechecked against the current allowlist.
- Rotate keys using `wrangler secret put`; never store a key in `lab-config.json`, GitHub Pages, a URL, or a chat message.
- Frontend rollback: clear `api_origin`, rebuild and publish. This removes the public connection, but does not stop direct backend usage by already signed-in clients; pause the Worker too if needed.
- Do not enable invocation URL logging or tracing on auth endpoints: callback URLs contain short-lived OAuth codes. Application logs contain only enumerated failure status; never add request bodies, cookies, Authorization headers, or raw provider errors. Avoid `wrangler tail` while real sign-ins or sensitive requests are running.
- A failure in the counter store stops requests; the Worker does not fall back to unmetered operation. Leases expire after crashes; quotas are not refunded.
- This is an invite-only pilot, not a general public service. Before opening registration, add account administration, abuse monitoring, a privacy notice/retention review, load testing and explicit operating budgets. There is no notebook sync, multi-tab synchronization, or independent verification of generated research claims.

## Implementation references

[GitHub OAuth and PKCE](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps), [Cloudflare Workers best practices](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/), [Durable Object transactions](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/), [Workers rate limits](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/), [Cloudflare testing](https://developers.cloudflare.com/workers/testing/vitest-integration/write-your-first-test/), [Cloudflare plan limits](https://developers.cloudflare.com/durable-objects/platform/pricing/).
