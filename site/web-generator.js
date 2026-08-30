/** Browser twin of the desktop tools — Inkscape / Blender option parity. */
(function () {
  const cfg = window.SITE_CONFIG || {};
  const bases = [cfg.apiBase, ...(cfg.apiFallbacks || [])].filter(Boolean);

  const PAID = new Set(["svg", "glb", "stl", "json", "csv"]);
  const KEY_STORE = "monotile.webgen.apiKey.v1";
  const COLOR_MODES = new Set(["greyscale", "random", "mystics", "rainbow"]);

  const GREY_FILL = "#cdd6ea";
  const GREY_STROKE = "#171b38";
  const LABEL_COLORS = {
    Gamma: "#E8B923",
    Delta: "#2E86AB",
    Theta: "#A23B72",
    Lambda: "#F18F01",
    Xi: "#C73E1D",
    Pi: "#3B1F2B",
    Sigma: "#44AF69",
    Phi: "#5C4D7D",
    Psi: "#9B5DE5",
    Gamma1: "#F4D35E",
    Gamma2: "#FFE066",
  };

  const el = {
    form: document.querySelector("#webgenForm"),
    shape: document.querySelector("#wgShape"),
    sizeRect: document.querySelector("#wgSizeRect"),
    sizeSingle: document.querySelector("#wgSizeSingle"),
    sizeLabel: document.querySelector("#wgSizeLabel"),
    size: document.querySelector("#wgSize"),
    width: document.querySelector("#wgWidth"),
    height: document.querySelector("#wgHeight"),
    tileSize: document.querySelector("#wgTileSize"),
    sideStyle: document.querySelector("#wgSideStyle"),
    amplitude: document.querySelector("#wgAmplitude"),
    ampWrap: document.querySelector("#wgAmpWrap"),
    wavySegs: document.querySelector("#wgWavySegs"),
    wavyWrap: document.querySelector("#wgWavyWrap"),
    color: document.querySelector("#wgColor"),
    colorWrap: document.querySelector("#wgColorWrap"),
    format: document.querySelector("#wgFormat"),
    depth: document.querySelector("#wgDepth"),
    depthWrap: document.querySelector("#wgDepthWrap"),
    compact: document.querySelector("#wgCompact"),
    compactWrap: document.querySelector("#wgCompactWrap"),
    key: document.querySelector("#wgKey"),
    getKey: document.querySelector("#wgGetKey"),
    buyDayPass: document.querySelector("#wgBuyDayPass"),
    upgrade: document.querySelector("#wgUpgrade"),
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

  function setDisabled(wrap, input, disabled) {
    if (input) input.disabled = disabled;
    if (wrap) wrap.classList.toggle("is-disabled", disabled);
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
    setDisabled(el.depthWrap, el.depth, !needsDepth);
    if (!needsDepth) el.depth.value = "0";

    const style = el.sideStyle.value;
    const styled = style !== "flat";
    setDisabled(el.ampWrap, el.amplitude, !styled);
    setDisabled(el.wavyWrap, el.wavySegs, style !== "wavy");

    const visual = fmt === "svg" || fmt === "png" || fmt === "jpg";
    setDisabled(el.colorWrap, el.color, !visual);
    setDisabled(el.compactWrap, el.compact, fmt !== "svg");

    if (el.upgrade) el.upgrade.hidden = !PAID.has(fmt);
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

  function paletteEntry(fill) {
    return { fill, stroke: GREY_STROKE };
  }

  function colorRequestFields(mode) {
    const colorMode = COLOR_MODES.has(mode) ? mode : "greyscale";
    if (colorMode === "random") {
      return {
        svg_fill: GREY_FILL,
        svg_stroke: GREY_STROKE,
        svg_deterministic_palette: true,
      };
    }
    if (colorMode === "mystics") {
      return {
        svg_fill: GREY_FILL,
        svg_stroke: GREY_STROKE,
        palette_by_label: {
          Gamma: paletteEntry("#E8B923"),
          Gamma1: paletteEntry("#F4D35E"),
          Gamma2: paletteEntry("#FFE066"),
          "*": paletteEntry("#b8becc"),
        },
      };
    }
    if (colorMode === "rainbow") {
      const palette = Object.fromEntries(
        Object.entries(LABEL_COLORS).map(([label, fill]) => [label, paletteEntry(fill)])
      );
      palette["*"] = paletteEntry(GREY_FILL);
      return {
        svg_fill: GREY_FILL,
        svg_stroke: GREY_STROKE,
        palette_by_label: palette,
      };
    }
    return {
      svg_fill: GREY_FILL,
      svg_stroke: GREY_STROKE,
      svg_deterministic_palette: false,
    };
  }

  function buildBody() {
    const fmt = el.format.value;
    const scale = Math.max(0.05, Number(el.tileSize.value) || 1);
    const body = {
      mask: buildMask(),
      formats: [fmt],
      scale,
      stl_extrusion_mm: Number(el.depth.value) || 0,
      png_width_px: 1200,
      png_height_px: 1200,
      jpg_width_px: 1200,
      jpg_height_px: 1200,
    };

    const style = (el.sideStyle.value || "flat").toLowerCase();
    if (style !== "flat") {
      body.side_style = style;
      body.side_style_amplitude = Math.max(
        0,
        Math.min(0.75, Number(el.amplitude.value) || 0.12)
      );
      if (style === "wavy") {
        body.side_style_wavy_segments = Math.max(
          4,
          Math.min(64, Number(el.wavySegs.value) || 10)
        );
      }
    }

    if (fmt === "svg" || fmt === "png" || fmt === "jpg") {
      Object.assign(body, colorRequestFields(el.color.value));
    }
    if (fmt === "svg") {
      body.svg_compact = el.compact.value !== "false";
    }
    return body;
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

  async function startCheckout(plan = "day_pass") {
    setStatus("Opening checkout…");
    try {
      const res = await apiFetch("/v1/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan, return_to: "web" }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok || !payload.checkout_url) {
        location.href = plan === "day_pass" ? "pricing.html#pricing" : "pricing.html";
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
        "SVG and 3D need a paid key.\n\n$5 Day Pass — 24 hours, full exports, no subscription.\nPNG/JPG stay free.\n\nOpen checkout now?"
      );
      if (go) startCheckout("day_pass");
      return;
    }
    try {
      localStorage.setItem(KEY_STORE, key);
    } catch (_) {}

    el.make.disabled = true;
    el.preview.hidden = true;
    el.downloads.replaceChildren();
    setStatus("Working…");

    const body = buildBody();

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
          const go = confirm(`${msg}\n\nTry a $5 Day Pass for 24 hours of SVG/3D exports?`);
          if (go) startCheckout("day_pass");
          setStatus("Need a paid key for that format.");
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
  el.sideStyle.addEventListener("change", refreshFields);
  el.getKey.addEventListener("click", () => startCheckout("day_pass"));
  if (el.buyDayPass) el.buyDayPass.addEventListener("click", () => startCheckout("day_pass"));
  el.form.addEventListener("submit", runJob);
  refreshFields();
})();
