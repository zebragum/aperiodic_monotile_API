/** Mint an API key after Stripe Checkout — shared by docs.html and web.html. */
(function () {
  const cfg = window.SITE_CONFIG || {};
  const bases = [cfg.apiBase, ...(cfg.apiFallbacks || [])].filter(Boolean);
  const SESSION_STORE_KEY = "monotile.lastCheckoutSession.v1";

  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session_id");
  const checkoutFlag = params.get("checkout");

  function rememberSessionId(id) {
    if (!id) return;
    try {
      localStorage.setItem(SESSION_STORE_KEY, id);
    } catch (_) {}
  }

  function lastKnownSessionId() {
    try {
      return localStorage.getItem(SESSION_STORE_KEY) || "";
    } catch (_) {
      return "";
    }
  }

  function clearSessionId() {
    try {
      localStorage.removeItem(SESSION_STORE_KEY);
    } catch (_) {}
  }

  if (sessionId) rememberSessionId(sessionId);

  async function apiFetch(path, options = {}) {
    let lastErr;
    for (const base of bases) {
      try {
        return await fetch(`${base}${path}`, options);
      } catch (err) {
        lastErr = err;
      }
    }
    throw lastErr || new Error("Network error");
  }

  function tierLabel(tier) {
    if (tier === "tier_day_pass") return "Day Pass (24 hours of SVG/3D exports)";
    if (tier === "tier_teams") return "Pro SVG/3D access";
    if (tier === "tier_solo") return "Solo SVG/3D access";
    return "paid SVG/3D access";
  }

  window.MonotileCheckoutClaim = {
    shouldRun() {
      return checkoutFlag === "success" || Boolean(sessionId || lastKnownSessionId());
    },

    async claim(options = {}) {
      const claimBox = document.querySelector(options.claimBox || "#checkoutClaim");
      const keyInput = document.querySelector(options.keyInput || "#wgKey");
      const onSuccess = typeof options.onSuccess === "function" ? options.onSuccess : null;
      const cleanUrl = options.cleanUrl || null;

      const render = (state, payload) => {
        if (!claimBox) return;
        claimBox.hidden = false;
        claimBox.replaceChildren();

        if (state === "loading") {
          const p = document.createElement("p");
          p.textContent = "Checkout complete. Minting your API key…";
          claimBox.appendChild(p);
          return;
        }

        if (state === "success") {
          const heading = document.createElement("strong");
          heading.textContent = `Thank you! You now have ${tierLabel(payload.tier)}.`;
          const code = document.createElement("code");
          code.textContent = payload.api_key;
          const note = document.createElement("p");
          note.textContent =
            "Your API key is shown once. We saved it in this browser for the web generator.";
          claimBox.append(heading, code, note);
          if (keyInput) keyInput.value = payload.api_key;
          try {
            localStorage.setItem("monotile.webgen.apiKey.v1", payload.api_key);
          } catch (_) {}
          if (cleanUrl) history.replaceState(null, "", cleanUrl);
          clearSessionId();
          if (onSuccess) onSuccess(payload);
          return;
        }

        if (state === "already_claimed") {
          const heading = document.createElement("strong");
          heading.textContent = "This checkout was already claimed.";
          const note = document.createElement("p");
          const keyPrefix = payload.key_prefix ? `Key prefix: ${payload.key_prefix}.` : "";
          note.textContent = `${keyPrefix} Paste your saved key below, or contact support with your checkout email.`;
          claimBox.append(heading, note);
          if (cleanUrl) history.replaceState(null, "", cleanUrl);
          clearSessionId();
          return;
        }

        if (state === "error") {
          const heading = document.createElement("strong");
          heading.textContent = "Could not mint your API key yet.";
          const reason = document.createElement("p");
          const detail =
            (payload && payload.message) ||
            "Transient error. Wait a few seconds and retry.";
          reason.textContent = detail;
          const retry = document.createElement("button");
          retry.type = "button";
          retry.className = "button";
          retry.textContent = "Retry";
          retry.addEventListener("click", () => void run());
          claimBox.append(heading, reason, retry);
        }
      };

      async function run() {
        const id = sessionId || lastKnownSessionId();
        if (!id) return;
        render("loading");
        try {
          const response = await apiFetch("/v1/billing/claim-key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: id }),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            const err = (payload && payload.error) || {};
            render("error", { message: err.message || `HTTP ${response.status}` });
            return;
          }
          if (payload.api_key) {
            render("success", payload);
          } else {
            render("already_claimed", payload);
          }
        } catch (err) {
          console.error(err);
          render("error", { message: "Network error reaching the API." });
        }
      }

      await run();
    },
  };
})();
