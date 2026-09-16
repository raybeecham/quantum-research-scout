import { z } from "zod";
import { authenticate, startLogin, finishLogin } from "./auth";
import { assist, generate, selectedProvider } from "./providers";
import { searchPapers } from "./papers";
import { questionSchema, readingSchema, providerSchema, searchSchema } from "./validation";
import { AppEnv, LabError, boundedText, day, fail, hash, httpsOrigin, limits } from "./support";
export { AuthRecord, DailyBudget } from "./storage";

async function route(request: Request, env: AppEnv): Promise<Response> {
  const url = new URL(request.url);
  httpsOrigin(env.PUBLIC_ORIGIN);
  httpsOrigin(env.BACKEND_ORIGIN);
  if (url.origin !== env.BACKEND_ORIGIN) fail(403, "origin", "Unexpected backend origin.");
  limits(env); // Invalid configuration fails closed.
  const path = url.pathname,
    origin = request.headers.get("Origin");
  if (path.startsWith("/api/") && origin !== env.PUBLIC_ORIGIN)
    fail(403, "origin", "This origin is not allowed.");
  if (request.method === "OPTIONS" && path.startsWith("/api/")) {
    if (!["GET", "POST"].includes(request.headers.get("Access-Control-Request-Method") || ""))
      fail(405, "method", "Method not allowed.");
    const names = (request.headers.get("Access-Control-Request-Headers") || "")
      .toLowerCase()
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);
    if (names.some(n => !["authorization", "content-type"].includes(n)))
      fail(403, "headers", "Headers not allowed.");
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Methods": "GET, POST",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Max-Age": "600",
      },
    });
  }
  if (
    !(
      await env.EDGE_LIMIT.limit({
        key: await hash(request.headers.get("CF-Connecting-IP") || "unknown"),
      })
    ).success
  )
    fail(429, "rate_limit", "Too many requests. Please wait.");
  if (request.method === "GET" && path === "/api/lab/health")
    return Response.json({
      service: "scout-hosted-lab",
      enabled: env.LAB_ENABLED === "true",
      sign_in: "/auth/start",
    });
  if (env.LAB_ENABLED !== "true")
    fail(
      503,
      "disabled",
      "The hosted lab is paused by the operator. Your saved work is unaffected.",
    );
  if (request.method === "GET" && path === "/auth/start") return startLogin(request, env);
  if (request.method === "GET" && path === "/auth/callback") return finishLogin(request, env);
  if (!path.startsWith("/api/lab/")) fail(404, "not_found", "Not found.");
  const { user, record } = await authenticate(request, env);
  const budget = env.BUDGET.getByName(day());
  if (request.method === "GET" && path === "/api/lab/config")
    return Response.json({
      hosted: true,
      user: user.login,
      providers: { gemini: Boolean(env.GEMINI_API_KEY), groq: Boolean(env.GROQ_API_KEY) },
      usage: await budget.usage(user.id),
    });
  if (request.method !== "POST") fail(405, "method", "Method not allowed.");
  if (request.headers.get("Content-Type") !== "application/json")
    fail(415, "content_type", "Use application/json.");
  if (path === "/api/lab/logout") {
    await record.revoke();
    return Response.json({ signed_out: true });
  }
  if (!["/api/lab/generate", "/api/lab/read", "/api/lab/papers"].includes(path))
    fail(404, "not_found", "Not found.");
  // Stream cap applies even to absent or forged Content-Length headers.
  const raw: unknown = JSON.parse(await boundedText(request, 24000));
  const search = path.endsWith("/papers"),
    read = path.endsWith("/read");
  if (search) {
    const data = searchSchema.parse(raw);
    const reservation = await budget.reserve(user.id, "search", 0);
    if (!reservation.ok) fail(429, "limit", reservation.error);
    try {
      return Response.json(await searchPapers(data.query));
    } finally {
      await budget.finish(user.id, "search", reservation.lease!);
    }
  }
  const consent = providerSchema.parse(raw);
  if (read && consent.reading_consent !== true)
    fail(400, "consent", "Explicit consent is required for reading assistance.");
  const input = read ? readingSchema.parse(raw) : questionSchema.parse(raw);
  selectedProvider(env, consent.provider); // Missing keys do not consume call slots.
  const reservation = await budget.reserve(user.id, "ai", read ? 1 : 2);
  if (!reservation.ok) fail(429, "limit", reservation.error);
  try {
    // Only allowlisted source fields are sent, never arbitrary client data or private notes.
    const result = read
      ? await assist(env, consent.provider, readingSchema.parse(input))
      : await generate(env, consent.provider, questionSchema.parse(input));
    return Response.json(result);
  } finally {
    await budget.finish(user.id, "ai", reservation.lease!);
  }
}

export default {
  async fetch(request: Request, env: AppEnv): Promise<Response> {
    let response: Response;
    try {
      response = await route(request, env);
    } catch (error) {
      const known = error instanceof LabError;
      const invalid = error instanceof z.ZodError || error instanceof SyntaxError;
      const status = known ? error.status : invalid ? 400 : 503;
      // Log only an enumerated status, never URLs, auth codes, topics, keys or error payloads.
      if (status >= 500) console.error(JSON.stringify({ event: "lab_failure", status }));
      response = Response.json(
        {
          error: known
            ? error.message
            : invalid
              ? "Invalid or oversized request fields."
              : "Lab service unavailable. No automatic retry was made.",
          code: known ? error.code : invalid ? "validation" : "service",
        },
        { status },
      );
    }
    const headers = new Headers(response.headers);
    headers.set("Cache-Control", "no-store");
    headers.set("Referrer-Policy", "no-referrer");
    headers.set("X-Content-Type-Options", "nosniff");
    headers.set("X-Frame-Options", "DENY");
    headers.set("Vary", "Origin");
    if (!headers.has("Content-Security-Policy"))
      headers.set(
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
      );
    if (request.headers.get("Origin") === env.PUBLIC_ORIGIN)
      headers.set("Access-Control-Allow-Origin", env.PUBLIC_ORIGIN);
    return new Response(response.body, { status: response.status, headers });
  },
} satisfies ExportedHandler<AppEnv>;
