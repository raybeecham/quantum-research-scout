import { env } from "cloudflare:workers";
import { runInDurableObject } from "cloudflare:test";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import worker from "../src/index";
import { day, hash, randomToken, boundedText, upstream, AppEnv } from "../src/support";
import { questionSchema, modelSchema, revisedSchema } from "../src/validation";
import { parseArxiv, parseCrossref } from "../src/papers";

const origin = "https://raybeecham.github.io",
  backend = "https://lab.example.com";
const settings: AppEnv = {
  ...env,
  BACKEND_ORIGIN: backend,
  LAB_ENABLED: "true",
  ALLOWED_GITHUB_IDS: "123,456",
  GITHUB_CLIENT_ID: "test-client",
  GITHUB_CLIENT_SECRET: "fixture-secret",
  GEMINI_API_KEY: "fixture-gemini",
  GROQ_API_KEY: "fixture-groq",
};
const input = {
  interest: "PQC discovery",
  lens: "pqc",
  sources: [],
  provider: "gemini",
  consent: true,
};
const candidate = {
  question: "Which artifacts are missed?",
  motivation: "Measure inventory accuracy",
  gap: "Hypothesis only",
  hypothesis: "Configuration changes recall",
  method: "Seeded benchmark",
  feasibility: "Laptop pilot",
  next: "Search prior work",
  source_ids: [],
  critique: {
    changes: "Bounded claim",
    ground_truth: "Seeded reference",
    alignment: "Recall by artifact",
    remaining_concerns: "Synthetic suite limits",
  },
};
const answer = { candidates: [candidate, candidate, candidate] };
const gemini = () =>
  Response.json({
    candidates: [{ finishReason: "STOP", content: { parts: [{ text: JSON.stringify(answer) }] } }],
  });
async function session(id = "123") {
  const token = randomToken();
  await env.AUTH.getByName("session:" + (await hash(token))).create(
    { kind: "session", id, login: "test-researcher" },
    3600000,
  );
  return token;
}
function request(
  path: string,
  token = "",
  body?: unknown,
  options: RequestInit = {},
  config: AppEnv = settings,
) {
  return worker.fetch(
    new Request(backend + path, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        Origin: origin,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      ...options,
    }),
    config,
  );
}
beforeEach(async () => {
  await runInDurableObject(env.BUDGET.getByName(day()), (_instance, state) => {
    state.storage.sql.exec("DELETE FROM counters");
  });
  // No unit test may use live outbound traffic or real provider credentials.
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network disabled in tests"));
});
afterEach(() => vi.restoreAllMocks());

describe("upstream runtime compatibility", () => {
  it("constructs a real Workers request and refuses redirects", async () => {
    vi.mocked(fetch).mockImplementation(async (url, init) => {
      const outbound = new Request(url, init);
      expect(outbound.redirect).toBe("manual");
      return new Response(null, { status: 302, headers: { Location: "https://example.com" } });
    });
    await expect(upstream("https://github.com/login/oauth/access_token", {
      method: "POST", body: "fixture",
    })).rejects.toMatchObject({ code: "upstream", message: expect.stringContaining("HTTP 302") });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe("authentication and boundaries", () => {
  it("requires authentication and never leaks token/config secrets", async () => {
    const r = await request("/api/lab/config");
    expect(r.status).toBe(401);
    expect(await r.text()).not.toContain("fixture");
    expect(r.headers.get("Cache-Control")).toBe("no-store");
  });
  it("rejects arbitrary origins and forged CORS preflights", async () => {
    const r = await request("/api/lab/config", "", undefined, {
      headers: { Origin: "https://evil.example" },
    });
    expect(r.status).toBe(403);
    expect(r.headers.has("Access-Control-Allow-Origin")).toBe(false);
    const options = await request("/api/lab/generate", "", undefined, {
      method: "OPTIONS",
      headers: {
        Origin: origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
      },
    });
    expect(options.status).toBe(204);
    expect(options.headers.get("Access-Control-Allow-Origin")).toBe(origin);
    expect(
      (
        await request("/api/lab/generate", "", undefined, {
          method: "OPTIONS",
          headers: { Origin: origin, "Access-Control-Request-Method": "DELETE" },
        })
      ).status,
    ).toBe(405);
  });
  it("rejects removed users on every request", async () => {
    const t = await session("456");
    expect((await request("/api/lab/config", t)).status).toBe(200);
    expect(
      (
        await request(
          "/api/lab/config",
          t,
          undefined,
          {},
          { ...settings, ALLOWED_GITHUB_IDS: "123" },
        )
      ).status,
    ).toBe(401);
  });
  it("expires and revokes sessions", async () => {
    const t = await session();
    expect((await request("/api/lab/logout", t, {})).status).toBe(200);
    expect((await request("/api/lab/config", t)).status).toBe(401);
    const expired = await session();
    await runInDurableObject(
      env.AUTH.getByName("session:" + (await hash(expired))),
      (_instance, state) => state.storage.sql.exec("UPDATE record SET expires=0"),
    );
    expect((await request("/api/lab/config", expired)).status).toBe(401);
  });
  it("fails closed when disabled, unconfigured or limits invalid", async () => {
    expect(
      (await request("/api/lab/config", "", undefined, {}, { ...settings, LAB_ENABLED: "false" }))
        .status,
    ).toBe(503);
    expect(
      (
        await request(
          "/api/lab/config",
          "",
          undefined,
          {},
          { ...settings, GLOBAL_DAILY_CALLS: "NaN" },
        )
      ).status,
    ).toBe(503);
    expect(
      (
        await request(
          "/api/lab/config",
          "",
          undefined,
          {},
          { ...settings, BACKEND_ORIGIN: "https://configure.invalid" },
        )
      ).status,
    ).toBe(503);
  });
  it("starts OAuth with PKCE, no repo scope and secure state cookie", async () => {
    const r = await request("/auth/start?challenge=" + "a".repeat(64));
    expect(r.status).toBe(302);
    const url = new URL(r.headers.get("Location")!);
    expect(url.origin).toBe("https://github.com");
    expect(url.searchParams.get("scope")).toBe("");
    expect(url.searchParams.get("code_challenge_method")).toBe("S256");
    expect(url.searchParams.get("code_challenge")).toHaveLength(43);
    expect(r.headers.get("Set-Cookie")).toContain("Secure; HttpOnly; SameSite=Lax");
  });
  it("rejects mismatched callback cookies without contacting GitHub", async () => {
    expect((await request("/auth/callback?state=" + "a".repeat(64) + "&code=foo")).status).toBe(
      403,
    );
    expect(fetch).not.toHaveBeenCalled();
  });
  it("completes OAuth once, with allowlisting and exact postMessage origin", async () => {
    const started = await request("/auth/start?challenge=" + "b".repeat(64));
    const state = new URL(started.headers.get("Location")!).searchParams.get("state")!;
    const options = { headers: { Cookie: started.headers.get("Set-Cookie")!.split(";")[0] } };
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        Response.json({ access_token: "fake-github-token", token_type: "bearer" }),
      )
      .mockResolvedValueOnce(Response.json({ id: 123, login: "tester" }));
    const completed = await request(
      "/auth/callback?state=" + state + "&code=foo",
      "",
      undefined,
      options,
    );
    expect(completed.status).toBe(200);
    const html = await completed.text();
    expect(html).toContain('"scout-lab-session"');
    expect(html).toContain(origin);
    expect(html).not.toContain("fake-github-token");
    expect(completed.headers.get("Content-Security-Policy")).toContain("script-src 'nonce-");
    expect(
      (await request("/auth/callback?state=" + state + "&code=foo", "", undefined, options)).status,
    ).toBe(403);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("does not issue sessions to uninvited GitHub accounts", async () => {
    const started = await request("/auth/start?challenge=" + "c".repeat(64));
    const state = new URL(started.headers.get("Location")!).searchParams.get("state")!;
    vi.mocked(fetch)
      .mockResolvedValueOnce(Response.json({ access_token: "fake", token_type: "bearer" }))
      .mockResolvedValueOnce(Response.json({ id: 999, login: "uninvited" }));
    const r = await request("/auth/callback?state=" + state + "&code=foo", "", undefined, {
      headers: { Cookie: started.headers.get("Set-Cookie")!.split(";")[0] },
    });
    expect(r.status).toBe(403);
    expect(await r.text()).not.toContain("scout-lab-session");
  });
});
describe("quota consistency", () => {
  it("bounds simultaneous reservations and shares a cap across users", async () => {
    const b = env.BUDGET.getByName(day());
    for (let wave = 0; wave < 5; wave++) {
      const ids = [String(1000 + wave * 2), String(1001 + wave * 2)];
      const values = await Promise.all(ids.map(id => b.reserve(id, "ai", 2)));
      expect(values.every(v => v.ok)).toBe(true);
      for (let i = 0; i < 2; i++) if (values[i].ok) await b.finish(ids[i], "ai", values[i].lease!);
    }
    expect((await b.usage("123")).global_calls).toBe(20);
    expect((await b.reserve("999", "ai", 1)).ok).toBe(false);
  });
  it("blocks per-user concurrent requests and cannot unlock with an old lease", async () => {
    const b = env.BUDGET.getByName(day());
    const results = await Promise.all(Array.from({ length: 10 }, () => b.reserve("123", "ai", 2)));
    expect(results.filter(v => v.ok)).toHaveLength(1);
    await b.finish("123", "ai", "wrong-lease");
    expect((await b.reserve("123", "ai", 1)).ok).toBe(false);
    expect((await b.usage("123")).user_calls).toBe(2);
  });
  it("limits a user independently and preserves count on rejected reservations", async () => {
    const b = env.BUDGET.getByName(day());
    for (let i = 0; i < 5; i++) {
      const v = await b.reserve("123", "ai", 2);
      expect(v.ok).toBe(true);
      if (v.ok) await b.finish("123", "ai", v.lease);
      await runInDurableObject(b, (_instance, state) =>
        state.storage.sql.exec("UPDATE counters SET last_ai=0 WHERE id='123'"),
      );
    }
    expect((await b.reserve("123", "ai", 1)).ok).toBe(false);
    expect((await b.reserve("456", "ai", 1)).ok).toBe(true);
    expect((await b.usage("123")).user_calls).toBe(10);
  });
  it("separates day objects and paper search from AI slots", async () => {
    const b = env.BUDGET.getByName(day());
    expect((await b.reserve("123", "search", 0)).ok).toBe(true);
    const u = await b.usage("123");
    expect(u.user_searches).toBe(1);
    expect(u.user_calls).toBe(0);
    expect(
      (await env.BUDGET.getByName("another-day-" + randomToken()).usage("123")).global_calls,
    ).toBe(0);
  });
});
describe("AI contract and privacy", () => {
  it("reserves two slots and returns only critiqued candidates", async () => {
    const t = await session();
    vi.mocked(fetch).mockImplementation(async () => gemini());
    const r = await request("/api/lab/generate", t, { ...input, private_notes: "SECRET NOTE" });
    expect(r.status).toBe(200);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(JSON.stringify(vi.mocked(fetch).mock.calls)).not.toContain("SECRET NOTE");
    expect((await r.json<{ candidates: unknown[] }>()).candidates).toHaveLength(3);
    expect((await env.BUDGET.getByName(day()).usage("123")).user_calls).toBe(2);
  });
  it("counts failed attempts, sanitizes errors and never silently falls back", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("SECRET TOKEN", { status: 429 }));
    const r = await request("/api/lab/generate", await session(), input);
    expect(r.status).toBe(502);
    expect(await r.text()).not.toContain("SECRET TOKEN");
    expect(fetch).toHaveBeenCalledTimes(1);
    expect((await env.BUDGET.getByName(day()).usage("123")).user_calls).toBe(2);
  });
  it("rejects missing consent and unconfigured provider without spending", async () => {
    const t = await session();
    expect((await request("/api/lab/generate", t, { ...input, consent: false })).status).toBe(400);
    expect((await request("/api/lab/generate", t, { ...input, provider: "groq" })).status).toBe(
      400,
    );
    expect(
      (await request("/api/lab/generate", t, input, {}, { ...settings, GEMINI_API_KEY: "" }))
        .status,
    ).toBe(503);
    expect((await env.BUDGET.getByName(day()).usage("123")).user_calls).toBe(0);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("uses explicit Groq consent and the Groq endpoint for both calls", async () => {
    vi.mocked(fetch).mockImplementation(async () =>
      Response.json({
        choices: [{ finish_reason: "stop", message: { content: JSON.stringify(answer) } }],
      }),
    );
    const r = await request("/api/lab/generate", await session(), {
      ...input,
      provider: "groq",
      backup_consent: true,
    });
    expect(r.status).toBe(200);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(
      vi
        .mocked(fetch)
        .mock.calls.every(c => c[0] === "https://api.groq.com/openai/v1/chat/completions"),
    ).toBe(true);
  });
  it("withholds unknown citations and incomplete critique", async () => {
    const bad = { ...candidate, source_ids: ["invented"] };
    vi.mocked(fetch).mockResolvedValue(
      Response.json({
        candidates: [
          {
            finishReason: "STOP",
            content: { parts: [{ text: JSON.stringify({ candidates: [bad, bad, bad] }) }] },
          },
        ],
      }),
    );
    expect((await request("/api/lab/generate", await session(), input)).status).toBe(502);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("reading assistance is one slot and excludes private fields", async () => {
    vi.mocked(fetch).mockResolvedValue(
      Response.json({
        candidates: [
          {
            finishReason: "STOP",
            content: { parts: [{ text: '{"answer":"Interpretation, not a full-paper review"}' }] },
          },
        ],
      }),
    );
    const r = await request("/api/lab/read", await session(), {
      provider: "gemini",
      consent: true,
      reading_consent: true,
      title: "A paper",
      excerpt: "Public excerpt",
      task: "Explain this excerpt",
      private_notes: "SECRET NOTE",
    });
    expect(r.status).toBe(200);
    expect(JSON.stringify(vi.mocked(fetch).mock.calls)).not.toContain("SECRET NOTE");
    expect((await env.BUDGET.getByName(day()).usage("123")).user_calls).toBe(1);
  });
  it("bounds untrusted stream bodies without relying on Content-Length", async () => {
    const r = await request("/api/lab/generate", await session(), {
      ...input,
      junk: "x".repeat(25000),
    });
    expect(r.status).toBe(413);
    expect(fetch).not.toHaveBeenCalled();
    await expect(boundedText(new Response("x".repeat(30)), 20)).rejects.toThrow("size limit");
  });
  it("validates source URLs and creates structured provider schemas", () => {
    expect(
      questionSchema.safeParse({
        ...input,
        sources: [{ title: "bad", url: "http://user:pass@example.com", excerpt: "" }],
      }).success,
    ).toBe(false);
    expect(modelSchema(revisedSchema).type).toBe("object");
  });
});
describe("paper discovery", () => {
  it("parses index metadata and rejects XML entities", () => {
    expect(() => parseArxiv('<!DOCTYPE feed [<!ENTITY x "boom">]><feed/>')).toThrow();
    const result = parseArxiv(
      "<feed><entry><id>http://arxiv.org/abs/2501.01234v2</id><title>Quantum paper</title><published>2025-01-03</published><author><name>A Researcher</name></author><summary>Public abstract</summary></entry></feed>",
    );
    expect(result[0].url).toBe("https://arxiv.org/abs/2501.01234");
    expect(result[0].type).toBe("Preprint");
    expect(
      parseCrossref({
        message: { items: [{ title: ["Paper"], DOI: "10.1/a", type: "journal-article" }] },
      })[0].url,
    ).toBe("https://doi.org/10.1/a");
  });
  it("reports both index outages rather than claiming no literature", async () => {
    const r = await request("/api/lab/papers", await session(), {
      query: "PQC discovery",
      private_notes: "SECRET",
    });
    expect(r.status).toBe(200);
    const body = await r.json<{ warnings: string[]; papers: unknown[] }>();
    expect(body.warnings).toHaveLength(2);
    expect(body.papers).toHaveLength(0);
    expect((await env.BUDGET.getByName(day()).usage("123")).user_calls).toBe(0);
  });
});

describe("failure regressions", () => {
  it("withholds the draft when the critique response is incomplete", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(gemini())
      .mockResolvedValueOnce(
        Response.json({
          candidates: [
            {
              finishReason: "STOP",
              content: {
                parts: [
                  {
                    text: JSON.stringify({
                      candidates: [{ ...candidate, critique: {} }, candidate, candidate],
                    }),
                  },
                ],
              },
            },
          ],
        }),
      );
    const r = await request("/api/lab/generate", await session(), input);
    expect(r.status).toBe(502);
    expect(await r.text()).not.toContain("Which artifacts");
    expect(fetch).toHaveBeenCalledTimes(2);
    expect((await env.BUDGET.getByName(day()).usage("123")).user_calls).toBe(2);
  });
  it("rejects a truncated response even when its JSON is parseable", async () => {
    vi.mocked(fetch).mockResolvedValue(
      Response.json({
        candidates: [
          { finishReason: "MAX_TOKENS", content: { parts: [{ text: JSON.stringify(answer) }] } },
        ],
      }),
    );
    expect((await request("/api/lab/generate", await session(), input)).status).toBe(502);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("requires reading consent independently of generation consent", async () => {
    expect(
      (
        await request("/api/lab/read", await session(), {
          ...input,
          title: "Paper",
          excerpt: "Excerpt",
          task: "Explain this excerpt",
        })
      ).status,
    ).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("bounds search usage separately and does not refund failed searches", async () => {
    const b = env.BUDGET.getByName(day());
    for (let i = 0; i < 20; i++) {
      const r = await b.reserve("123", "search", 0);
      expect(r.ok).toBe(true);
      if (r.ok) await b.finish("123", "search", r.lease);
      await runInDurableObject(b, (_instance, state) => {
        state.storage.sql.exec("UPDATE counters SET last_search=0 WHERE id='123'");
      });
    }
    expect((await b.reserve("123", "search", 0)).ok).toBe(false);
    expect((await b.usage("123")).user_calls).toBe(0);
    expect((await b.usage("123")).user_searches).toBe(20);
  });
  it("caps global concurrency without consuming a rejected reservation", async () => {
    const b = env.BUDGET.getByName(day());
    const result = await Promise.all(
      ["101", "102", "103", "104"].map(id => b.reserve(id, "ai", 2)),
    );
    expect(result.filter(v => v.ok)).toHaveLength(2);
    expect((await b.usage("123")).global_calls).toBe(4);
  });
  it("expires consumed OAuth records and refuses replay after storage deletion", async () => {
    const state = randomToken();
    const record = env.AUTH.getByName("oauth:" + (await hash(state)));
    await record.create(
      { kind: "oauth", verifier: randomToken(), challenge: randomToken() },
      600000,
    );
    expect((await record.read(true))?.kind).toBe("oauth");
    expect(await record.read(true)).toBeNull();
    await record.revoke();
    expect(await record.read()).toBeNull();
  });
  it("closes every object schema required by Groq strict mode", () => {
    function inspect(value: unknown) {
      if (!value || typeof value !== "object") return;
      if (Array.isArray(value)) {
        value.forEach(inspect);
        return;
      }
      const row = value as Record<string, unknown>;
      if (row.type === "object") expect(row.additionalProperties).toBe(false);
      Object.values(row).forEach(inspect);
    }
    inspect(modelSchema(revisedSchema));
  });
});
