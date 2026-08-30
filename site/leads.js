/** Lightweight lead capture for pricing and generator pages. */
(function () {
  const cfg = window.SITE_CONFIG || {};
  const bases = [cfg.apiBase, ...(cfg.apiFallbacks || [])].filter(Boolean);

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

  function emailLooksValid(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  document.querySelectorAll("[data-lead-form]").forEach((form) => {
    const status = form.querySelector("[data-lead-status]");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const emailInput = form.querySelector('input[type="email"]');
      const email = (emailInput?.value || "").trim().toLowerCase();
      if (!emailLooksValid(email)) {
        if (status) status.textContent = "Enter a valid email address.";
        emailInput?.focus();
        return;
      }
      const submit = form.querySelector('button[type="submit"]');
      if (submit) submit.disabled = true;
      if (status) status.textContent = "Saving…";
      try {
        const response = await apiFetch("/v1/leads", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            source: form.getAttribute("data-lead-source") || "website",
            use_case: form.getAttribute("data-lead-use-case") || "",
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error((payload.detail && String(payload.detail)) || `HTTP ${response.status}`);
        }
        if (status) status.textContent = "Thanks — we'll email you when new packs and tools ship.";
        form.reset();
      } catch (err) {
        if (status) status.textContent = "Could not save. Try again or email zach@shopcloudburst.com.";
        console.error(err);
      } finally {
        if (submit) submit.disabled = false;
      }
    });
  });
})();
