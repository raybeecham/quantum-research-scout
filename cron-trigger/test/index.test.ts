import { describe, expect, it, vi } from "vitest";
import { dispatch, type TriggerEnv } from "../src/index";

const env = {
  REPOSITORY: "owner/repo",
  WORKFLOW_FILE: "hourly-news.yml",
  GITHUB_DISPATCH_TOKEN: "fixture-not-a-token",
} as TriggerEnv;

describe("dispatch", () => {
  it("starts the workflow on main as a cron slot", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 204 }));
    await dispatch(env, fetcher as typeof fetch);
    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(
      "https://api.github.com/repos/owner/repo/actions/workflows/hourly-news.yml/dispatches",
    );
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ ref: "main", inputs: { trigger: "cron" } });
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer fixture-not-a-token");
    expect(headers["User-Agent"]).toBeTruthy();
  });

  it("fails loudly without echoing the token", async () => {
    const fetcher = vi.fn(async () => new Response('{"message":"Bad credentials"}', { status: 401 }));
    const error = await dispatch(env, fetcher as typeof fetch).catch((e: Error) => e);
    expect(error).toBeInstanceOf(Error);
    expect((error as Error).message).toContain("HTTP 401");
    expect((error as Error).message).not.toContain("fixture-not-a-token");
  });

  it("refuses to run without a token", async () => {
    const fetcher = vi.fn();
    await expect(
      dispatch({ ...env, GITHUB_DISPATCH_TOKEN: undefined }, fetcher as typeof fetch),
    ).rejects.toThrow("GITHUB_DISPATCH_TOKEN is not set");
    expect(fetcher).not.toHaveBeenCalled();
  });
});
