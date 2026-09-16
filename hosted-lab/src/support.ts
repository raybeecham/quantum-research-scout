export type AppEnv = Env & {
  GITHUB_CLIENT_SECRET?: string;
  GEMINI_API_KEY?: string;
  GROQ_API_KEY?: string;
};

export class LabError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export function fail(status: number, code: string, message: string): never {
  throw new LabError(status, code, message);
}
export const randomToken = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, "0")).join(
    "",
  );
export async function digest(value: string) {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
}
export async function hash(value: string) {
  return Array.from(new Uint8Array(await digest(value)), b => b.toString(16).padStart(2, "0")).join(
    "",
  );
}
export async function equal(a: string, b: string) {
  return crypto.subtle.timingSafeEqual(await digest(a), await digest(b));
}
export const allowed = (env: AppEnv, id: string) =>
  /^\d+$/.test(id) &&
  env.ALLOWED_GITHUB_IDS.split(",")
    .map(s => s.trim())
    .filter(Boolean)
    .includes(id);
export function httpsOrigin(value: string) {
  const url = new URL(value);
  if (
    url.protocol !== "https:" ||
    url.origin !== value ||
    url.username ||
    url.password ||
    url.hostname.endsWith(".invalid")
  )
    throw new Error("Invalid deployment origin");
  return value;
}
export function limits(env: AppEnv) {
  const n = (s: string, max: number) => {
    const value = Number(s);
    if (!/^\d+$/.test(s) || !Number.isSafeInteger(value) || value < 1 || value > max)
      throw new Error("Invalid budget configuration");
    return value;
  };
  return {
    userCalls: n(env.USER_DAILY_CALLS, 100),
    globalCalls: n(env.GLOBAL_DAILY_CALLS, 1000),
    userSearches: n(env.USER_DAILY_SEARCHES, 100),
    globalSearches: n(env.GLOBAL_DAILY_SEARCHES, 1000),
  };
}
export const day = () => new Date().toISOString().slice(0, 10);
export async function boundedText(body: Request | Response, limit: number) {
  if (Number(body.headers.get("Content-Length")) > limit)
    fail(413, "too_large", "Payload exceeds the size limit.");
  const reader = body.body?.getReader();
  if (!reader) return "";
  let size = 0,
    text = "";
  const decoder = new TextDecoder();
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      size += chunk.value.byteLength;
      if (size > limit) {
        await reader.cancel();
        fail(413, "too_large", "Payload exceeds the size limit.");
      }
      text += decoder.decode(chunk.value, { stream: true });
    }
    return text + decoder.decode();
  } finally {
    reader.releaseLock();
  }
}
export async function upstream(
  url: string,
  init: RequestInit,
  max = 256_000,
  timeout = 70000,
): Promise<unknown> {
  try {
    const res = await fetch(url, {
      ...init,
      redirect: "error",
      signal: AbortSignal.timeout(timeout),
    });
    if (!res.ok) {
      await res.body?.cancel();
      fail(
        502,
        "upstream",
        `Upstream returned HTTP ${res.status}. No retry or provider switch was made.`,
      );
    }
    return JSON.parse(await boundedText(res, max));
  } catch (e) {
    if (e instanceof LabError) throw e;
    return fail(
      502,
      "upstream",
      "Upstream unavailable or returned an incomplete response. No automatic retry was made.",
    );
  }
}
