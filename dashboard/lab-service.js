/* Hosted sessions stay in memory, never in URLs, localStorage or notebook backups. */
(() => {
  "use strict";
  let backend = "",
    session = "",
    popup = null,
    challenge = "",
    loginTimer = null;
  const local = location.protocol === "http:" && location.hostname === "127.0.0.1";
  const changed = () => window.dispatchEvent(new Event("scout-lab-auth"));
  const error = (message, name = "LabConnectionError") =>
    Object.assign(new Error(message), { name });
  let setup = null;
  async function loadConfiguration() {
    if (local) return; // Never send the private lab's data to a hosted endpoint implicitly.
    try {
      const response = await fetch("lab-config.json", {
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) throw Error();
      const data = await response.json();
      if (!data.api_origin) return;
      const url = new URL(data.api_origin);
      if (
        url.protocol !== "https:" ||
        url.origin !== data.api_origin ||
        url.username ||
        url.password ||
        url.hostname.endsWith(".invalid")
      )
        throw Error();
      backend = url.origin;
    } catch {
      throw error(
        "Hosted lab configuration could not be loaded. Check the connection again or use the private lab.",
      );
    }
  }
  async function hostedConfig() {
    if (!setup)
      setup = loadConfiguration().catch(e => {
        setup = null;
        throw e;
      });
    await setup;
    if (!backend) return null;
    let response;
    try {
      response = await fetch(backend + (session ? "/api/lab/config" : "/api/lab/health"), {
        headers: session ? { Authorization: `Bearer ${session}` } : {},
        credentials: "omit",
        redirect: "error",
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
      if (response.status === 401) {
        session = "";
        throw error("Your hosted session expired. Sign in with GitHub again.", "LabSignInError");
      }
      if (!response.ok)
        throw error(
          "Hosted lab unavailable. Check the connection again; switching providers will not repair the server connection.",
        );
      const data = await response.json();
      if (!session) {
        if (!data.enabled)
          throw error(
            "The hosted lab is paused by the operator. Saved questions and notes remain available.",
          );
        throw error(
          "Hosted lab available. Sign in with your invited GitHub account to use AI and paper search.",
          "LabSignInError",
        );
      }
      if (data.hosted !== true || typeof data.user !== "string" || !data.usage) throw Error();
      return { ...data, token: session, apiBase: backend, hosted: true };
    } catch (e) {
      if (["LabConnectionError", "LabSignInError"].includes(e.name)) throw e;
      throw error(
        "Cannot reach the hosted lab. Check the connection again. Your saved work is unchanged.",
      );
    }
  }
  async function signIn() {
    // Open synchronously from the click so popup blockers do not discard the login window.
    if (!backend || (popup && !popup.closed))
      throw error("Finish or close the existing sign-in window first.");
    popup = window.open(
      "about:blank",
      "scout-github-" + crypto.randomUUID(),
      "width=620,height=740",
    );
    if (!popup) throw error("Allow popups for this site, then click Sign in with GitHub again.");
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    challenge = Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
    popup.location.href = backend + "/auth/start?challenge=" + challenge;
    clearTimeout(loginTimer);
    loginTimer = setTimeout(() => {
      challenge = "";
      popup = null;
      changed();
    }, 600000);
  }
  window.addEventListener("message", event => {
    if (
      !backend ||
      event.origin !== backend ||
      event.source !== popup ||
      !challenge ||
      event.data?.type !== "scout-lab-session" ||
      event.data.challenge !== challenge ||
      !/^[a-f0-9]{64}$/.test(event.data.token || "")
    )
      return;
    session = event.data.token;
    challenge = "";
    popup = null;
    clearTimeout(loginTimer);
    changed();
  });
  async function signOut() {
    const token = session;
    session = "";
    challenge = "";
    if (popup && !popup.closed) popup.close();
    popup = null;
    clearTimeout(loginTimer);
    changed();
    if (!token) return;
    const response = await fetch(backend + "/api/lab/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: "{}",
      credentials: "omit",
      redirect: "error",
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok && response.status !== 401)
      throw error(
        "Signed out in this tab, but server revocation failed. The session expires within one hour.",
      );
  }
  async function request(config, path, data, timeout) {
    if (!["generate", "papers", "read"].includes(path)) throw error("Unsupported lab request.");
    // Refuse a stale in-flight configuration after sign-out or account change.
    if (config.hosted && (!session || config.token !== session || config.apiBase !== backend))
      throw error("Sign in again before sending this request.", "LabSignInError");
    const headers = {
      "Content-Type": "application/json",
      ...(config.hosted
        ? { Authorization: `Bearer ${session}` }
        : { "X-Scout-Token": config.token }),
    };
    const response = await fetch((config.hosted ? backend + "/" : "") + "api/lab/" + path, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
      credentials: "omit",
      redirect: "error",
      signal: AbortSignal.timeout(timeout),
    });
    if (config.hosted && config.token !== session) {
      await response.body?.cancel();
      throw error(
        "Session changed while the request was running. The response was discarded; call slots may still have been used.",
        "LabSignInError",
      );
    }
    if (config.hosted && response.status === 401) {
      session = "";
      changed();
    }
    return response;
  }
  window.ScoutLab = {
    hostedConfig,
    signIn,
    signOut,
    request,
    mode: () => (backend ? "hosted" : local ? "local" : "unconfigured"),
    signedIn: () => Boolean(session),
  };
})();
