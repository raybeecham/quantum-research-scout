/* Starts the hourly news workflow from Cloudflare's scheduler. GitHub can drop its own
   scheduled events, so this dispatches the same slots with trigger=cron, which the
   workflow's due gate treats exactly like a scheduled slot. */

export type TriggerEnv = Env & { GITHUB_DISPATCH_TOKEN?: string };

export async function dispatch(env: TriggerEnv, fetcher: typeof fetch = fetch): Promise<void> {
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error("GITHUB_DISPATCH_TOKEN is not set");
  const url = `https://api.github.com/repos/${env.REPOSITORY}/actions/workflows/${env.WORKFLOW_FILE}/dispatches`;
  const response = await fetcher(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "frontier-hourly-trigger",
    },
    body: JSON.stringify({ ref: "main", inputs: { trigger: "cron" } }),
  });
  if (!response.ok) {
    // GitHub's message (expired token, unknown input) is safe to log; it never echoes the token.
    const detail = (await response.text()).slice(0, 300);
    throw new Error(`GitHub dispatch failed: HTTP ${response.status} ${detail}`);
  }
}

export default {
  async scheduled(_controller, env) {
    // A thrown error marks the cron invocation as failed in Workers logs.
    await dispatch(env);
  },
} satisfies ExportedHandler<TriggerEnv>;
