import { DurableObject } from "cloudflare:workers";
import { z } from "zod";
import { limits } from "./support";

const authSchema = z.discriminatedUnion("kind", [
  z.object({ kind: z.literal("oauth"), verifier: z.string(), challenge: z.string() }),
  z.object({ kind: z.literal("session"), id: z.string(), login: z.string() }),
]);
type AuthValue = z.infer<typeof authSchema>;
export class AuthRecord extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    void this.ctx.blockConcurrencyWhile(async () => {
      this.ctx.storage.sql.exec(
        "CREATE TABLE IF NOT EXISTS record (id INTEGER PRIMARY KEY, value TEXT NOT NULL, expires INTEGER NOT NULL)",
      );
    });
  }
  async create(value: AuthValue, ttl: number) {
    if (![600000, 3600000].includes(ttl)) throw new Error("Invalid TTL");
    const expires = Date.now() + ttl;
    this.ctx.storage.sql.exec(
      "INSERT INTO record VALUES (1, ?, ?)",
      JSON.stringify(authSchema.parse(value)),
      expires,
    );
    await this.ctx.storage.setAlarm(expires);
  }
  read(consume = false): AuthValue | null {
    return this.ctx.storage.transactionSync(() => {
      // deleteAll() in an alarm also removes SQLite tables while this instance may
      // still be alive. An expired/revoked record must mean unauthenticated, not 503.
      if (
        !this.ctx.storage.sql
          .exec("SELECT name FROM sqlite_master WHERE type='table' AND name='record'")
          .toArray().length
      )
        return null;
      const row = this.ctx.storage.sql
        .exec<{ value: string; expires: number }>("SELECT value, expires FROM record WHERE id=1")
        .toArray()[0];
      if (consume || (row && row.expires <= Date.now()))
        this.ctx.storage.sql.exec("DELETE FROM record WHERE id=1");
      return row && row.expires > Date.now() ? authSchema.parse(JSON.parse(row.value)) : null;
    });
  }
  async revoke() {
    await this.ctx.storage.deleteAll();
  }
  async alarm() {
    await this.ctx.storage.deleteAll();
  }
}

type Counts = {
  id: string;
  calls: number;
  searches: number;
  last_ai: number;
  last_search: number;
  lease_ai: string;
  lease_search: string;
  until_ai: number;
  until_search: number;
};
const empty = (id: string): Counts => ({
  id,
  calls: 0,
  searches: 0,
  last_ai: 0,
  last_search: 0,
  lease_ai: "",
  lease_search: "",
  until_ai: 0,
  until_search: 0,
});
// One coordination atom per deployment/UTC day, ONLY quota bookkeeping; provider I/O
// stays outside the DO. Sessions are separately sharded. Global and user caps share
// one short synchronous transaction, so concurrent users cannot overspend the cap.
export class DailyBudget extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    void this.ctx.blockConcurrencyWhile(async () => {
      this.ctx.storage.sql.exec(
        "CREATE TABLE IF NOT EXISTS counters (id TEXT PRIMARY KEY, calls INTEGER, searches INTEGER, last_ai INTEGER, last_search INTEGER, lease_ai TEXT, lease_search TEXT, until_ai INTEGER, until_search INTEGER)",
      );
      if (!(await this.ctx.storage.getAlarm()))
        await this.ctx.storage.setAlarm(Date.now() + 172800000);
    });
  }
  private counts(id: string) {
    return (
      this.ctx.storage.sql.exec<Counts>("SELECT * FROM counters WHERE id=?", id).toArray()[0] ||
      empty(id)
    );
  }
  usage(id: string) {
    const user = this.counts(id),
      total = this.counts("*");
    return {
      user_calls: user.calls,
      global_calls: total.calls,
      user_searches: user.searches,
      global_searches: total.searches,
      ...limits(this.env),
      resets: "midnight UTC",
    };
  }
  reserve(id: string, kind: "ai" | "search", calls: number) {
    if (
      !/^\d+$/.test(id) ||
      !["ai", "search"].includes(kind) ||
      (kind === "ai" ? ![1, 2].includes(calls) : calls !== 0)
    )
      throw new Error("Invalid reservation");
    return this.ctx.storage.transactionSync(() => {
      const now = Date.now(),
        user = this.counts(id),
        total = this.counts("*"),
        cap = limits(this.env);
      const busy = kind === "ai" ? user.until_ai : user.until_search;
      const last = kind === "ai" ? user.last_ai : user.last_search;
      if (busy > now || (last && now - last < (kind === "ai" ? 10000 : 4000)))
        return {
          ok: false as const,
          error: "A request is running or the cooldown is active. Please wait.",
        };
      if (
        kind === "ai" &&
        (user.calls + calls > cap.userCalls || total.calls + calls > cap.globalCalls)
      )
        return {
          ok: false as const,
          error: "Daily AI limit reached. Both providers share this cap; resets at midnight UTC.",
        };
      if (
        kind === "search" &&
        (user.searches + 1 > cap.userSearches || total.searches + 1 > cap.globalSearches)
      )
        return {
          ok: false as const,
          error: "Daily paper-search limit reached; resets at midnight UTC.",
        };
      const active = this.ctx.storage.sql
        .exec<{ n: number }>(
          kind === "ai"
            ? "SELECT COUNT(*) n FROM counters WHERE until_ai > ?"
            : "SELECT COUNT(*) n FROM counters WHERE until_search > ?",
          now,
        )
        .one().n;
      if (active >= 2)
        return { ok: false as const, error: "The shared service is busy. Please try later." };
      const lease = crypto.randomUUID();
      if (kind === "ai") {
        user.calls += calls;
        total.calls += calls;
        user.last_ai = now;
        user.until_ai = now + 210000;
        user.lease_ai = lease;
      } else {
        user.searches++;
        total.searches++;
        user.last_search = now;
        user.until_search = now + 75000;
        user.lease_search = lease;
      }
      for (const row of [user, total])
        this.ctx.storage.sql.exec(
          "INSERT OR REPLACE INTO counters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
          row.id,
          row.calls,
          row.searches,
          row.last_ai,
          row.last_search,
          row.lease_ai,
          row.lease_search,
          row.until_ai,
          row.until_search,
        );
      return { ok: true as const, lease };
    });
  }
  finish(id: string, kind: "ai" | "search", lease: string) {
    // Compare a non-secret lease identifier; stale completions cannot clear newer work.
    if (kind === "ai")
      this.ctx.storage.sql.exec(
        "UPDATE counters SET until_ai=0, lease_ai='' WHERE id=? AND lease_ai=?",
        id,
        lease,
      );
    else
      this.ctx.storage.sql.exec(
        "UPDATE counters SET until_search=0, lease_search='' WHERE id=? AND lease_search=?",
        id,
        lease,
      );
  }
  async alarm() {
    await this.ctx.storage.deleteAll();
  }
}
