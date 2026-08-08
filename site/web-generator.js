/** Browser twin of the Windows Aperiodic Generator app. */
(function () {
  const cfg = window.SITE_CONFIG || {};
  const bases = [cfg.apiBase, ...(cfg.apiFallbacks || [])].filter(Boolean);

  const PAID = new Set(["svg", "glb", "stl", "json", "csv"]);
  const KEY_STORE = "monotile.webgen.apiKey.v1";

  const el = {
    form: document.querySelector("#webgenForm"),
    shape: document.querySelector("#wgShape"),
    sizeRect: document.querySelector("#wgSizeRect"),
    sizeSingle: document.querySelector("#wgSizeSingle"),
    sizeLabel: document.querySelector("#wgSizeLabel"),
    size: document.querySelector("#wgSize"),
    width: document.querySelector("#wgWidth"),
    height: document.querySelector("#wgHeight"),
    format: document.querySelector("#wgFormat"),
    depth: document.querySelector("#wgDepth"),
    depthWrap: document.querySelector("#wgDepthWrap"),
    key: document.querySelector("#wgKey"),
    getKey: document.querySelector("#wgGetKey"),
    make: document.querySelector("#wgMake"),
    status: document.querySelector("#wgStatus"),
    preview: document.querySelector("#wgPreview"),
    previewImg: document.querySelector("#wgPreviewImg"),
    downloads: document.querySelector("#wgDownloads"),
  };

  try {
    const saved = localStorage.getItem(KEY_STORE);
    if (saved && el.key) el.key.value = saved;
  } catch (_) {}

  function setStatus(msg) {
    if (el.status) el.status.textContent = msg;
  }

  function refreshFields() {
    const shape = el.shape.value;
    const isRect = shape === "rectangle";
    el.sizeRect.hidden = !isRect;
    el.sizeSingle.hidden = isRect;
    el.sizeLabel.textContent =
      {
        circle: "Radius",
        square: "Size",
        triangle: "Side length",
        regular_hexagon: "Radius",
      }[shape] || "Size";

    const fmt = el.format.value;
    const needsDepth = fmt === "glb" || fmt === "stl";
    el.depth.disabled = !needsDepth;
    el.depthWrap.classList.toggle("is-disabled", !needsDepth);
    if (!needsDepth) el.depth.value = "0";
  }

  function buildMask() {
    const shape = el.shape.value;
    const size = Number(el.size.value);
    const width = Number(el.width.value);
    const height = Number(el.height.value);
    if (shape === "circle") return { type: "circle", radius: size };
    if (shape === "square") return { type: "square", half_side: size };
    if (shape === "triangle") return { type: "triangle", side_length: size };
    if (shape === "regular_hexagon") return { type: "regular_hexagon", circumradius: size };
    return { type: "rectangle", width, height };
  }

  async function apiFetch(path, options = {}) {
    let lastErr;
    for (const base of bases) {
      try {
        const headers = {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(options.headers || {}),
        };
        const key = (el.key.value || "").trim();
        if (key) headers["X-API-Key"] = key;
        if ((options.method || "GET").toUpperCase() === "POST") {
          headers["Idempotency-Key"] =
            headers["Idempotency-Key"] ||
            (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
        }
        const res = await fetch(`${base}${path}`, { ...options, headers });
        return res;
      } catch (err) {
        lastErr = err;
      }
    }
    throw lastErr || new Error("Network error");
  }

  async function startCheckout() {
    setStatus("Opening checkout…");
    try {
      const res = await apiFetch("/v1/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan: "solo_monthly" }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok || !payload.checkout_url) {
        location.href = "pricing.html";
        return;
      }
      location.href = payload.checkout_url;
    } catch (_) {
      location.href = "pricing.html";
    }
  }

  function absoluteUrl(url) {
    if (/^https?:\/\//i.test(url)) return url;
    const base = bases[0] || "";
    return `${base}${url}`;
  }

  function showDownloads(urls) {
    el.downloads.replaceChildren();
    const entries = Object.entries(urls || {});
    if (!entries.length) {
      setStatus("Job finished, but no files came back.");
      return;
    }
    for (const [name, url] of entries) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = absoluteUrl(url);
      a.textContent = `Download ${name}`;
      a.download = name;
      a.rel = "noopener";
      li.append(a);
      el.downloads.append(li);
      if (/\.(png|jpe?g)$/i.test(name)) {
        el.preview.hidden = false;
        el.previewImg.src = absoluteUrl(url);
      }
    }
    setStatus("Done.");
  }

  async function runJob(event) {
    event.preventDefault();
    const fmt = el.format.value;
    const key = (el.key.value || "").trim();
    if (PAID.has(fmt) && !key) {
      const go = confirm(
        "SVG and 3D need an API key.\n\nPictures (PNG/JPG) are free.\n\nGet a key now?"
      );
      if (go) startCheckout();
      return;
    }
    try {
      localStorage.setItem(KEY_STORE, key);
    } catch (_) {}

    el.make.disabled = true;
    el.preview.hidden = true;
    el.downloads.replaceChildren();
    setStatus("Working…");

    const body = {
      mask: buildMask(),
      formats: [fmt],
      scale: 1,
      stl_extrusion_mm: Number(el.depth.value) || 0,
      png_width_px: 1200,
      png_height_px: 1200,
      jpg_width_px: 1200,
      jpg_height_px: 1200,
    };

    try {
      const createRes = await apiFetch("/v1/patch", {
        method: "POST",
        body: JSON.stringify(body),
      });
      const created = await createRes.json().catch(() => ({}));
      if (!createRes.ok) {
        const msg =
          (created.error && created.error.message) ||
          created.detail ||
          `HTTP ${createRes.status}`;
        if (createRes.status === 401 || createRes.status === 403 || createRes.status === 422) {
          const go = confirm(`${msg}\n\nGet a key?`);
          if (go) startCheckout();
          setStatus("Need a key for that format.");
          return;
        }
        throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
      }
      const jobId = created.job_id;
      if (!jobId) throw new Error("No job_id returned");

      let status = created.status || "queued";
      const deadline = Date.now() + 10 * 60 * 1000;
      while (Date.now() < deadline) {
        setStatus(`Status: ${status}`);
        if (status === "completed" || status === "failed" || status === "cancelled") break;
        await new Promise((r) => setTimeout(r, 1500));
        const jobRes = await apiFetch(`/v1/jobs/${jobId}`);
        const job = await jobRes.json().catch(() => ({}));
        status = job.status || status;
      }
      if (status !== "completed") throw new Error(`Job did not complete (${status})`);

      const urlRes = await apiFetch(`/v1/jobs/${jobId}/urls`);
      const urlPayload = await urlRes.json().catch(() => ({}));
      showDownloads(urlPayload.urls || {});
    } catch (err) {
      console.error(err);
      setStatus("Something went wrong.");
      alert(String(err.message || err).slice(0, 500));
    } finally {
      el.make.disabled = false;
    }
  }

  el.shape.addEventListener("change", refreshFields);
  el.format.addEventListener("change", refreshFields);
  el.getKey.addEventListener("click", startCheckout);
  el.form.addEventListener("submit", runJob);
  refreshFields();
})();
