const demoPresets = [
  {
    id: "circle-100u",
    src: "assets/examples/circle-100u.svg",
    alt: "A circular Spectre / Tile(1,1) monotile patch",
    headline: "Circle mask",
    extent: "~100-unit diameter · circle clip",
    approxTiles: "~1,036 tiles",
    rasterNote: "~1000px SVG canvas",
    formatsHint: "Pre-cached SVG; regenerate any extent via API"
  },
  {
    id: "rect-9x4",
    src: "assets/examples/rectangle-9x4.svg",
    alt: "A rectangular Spectre monotile patch",
    headline: "9∶4 rectangle",
    extent: "90 × 40 canonical units · axis-aligned rectangle",
    approxTiles: "~500 tiles",
    rasterNote: "900×400 SVG canvas",
    formatsHint: "Pre-cached SVG; regenerate via API"
  },
  {
    id: "tri-50u",
    src: "assets/examples/triangle-50u.svg",
    alt: "An equilateral triangular Spectre monotile patch",
    headline: "Equilateral triangle",
    extent: "50-unit edges · centroid-centered mask",
    approxTiles: "~166 tiles",
    rasterNote: "500×433 SVG canvas",
    formatsHint: "Pre-cached SVG; regenerate via API"
  }
];

const presetSelect = document.querySelector("#presetSelect");
const outlineStyleSelect = document.querySelector("#outlineStyleSelect");
const previewMagnifyRange = document.querySelector("#previewMagnifyRange");
const strokeRange = document.querySelector("#strokeRange");
const demoSvgHost = document.querySelector("#demoSvgHost");
const demoStats = document.querySelector("#demoStats");
const previewFrame = document.querySelector(".preview-frame");

/** Example SVGs ship with strokes at stroke-width 0.25 in canonical units. */
const DEMO_BASE_STROKE = 0.25;
const svgTextCache = new Map();
const checkoutButtons = [document.querySelector("#studioCheckout"), document.querySelector("#ctaCheckout")].filter(Boolean);
const checkoutStatus = document.querySelector("#checkoutStatus");
const leadForm = document.querySelector("#leadForm");
const apiBase = "https://aperiodic-monotile-api.onrender.com";

function currentPreset() {
  const id = presetSelect?.value ?? demoPresets[0].id;
  const found = demoPresets.find((p) => p.id === id);
  return found ?? demoPresets[0];
}

function renderStats(example) {
  if (!demoStats) return;
  demoStats.innerHTML = `
    <strong>${example.headline}</strong>
    <span>${example.extent}</span>
    <span>${example.approxTiles}</span>
    <span>${example.rasterNote}</span>
    <span>${example.formatsHint}</span>
  `;
}

function computeCanonicalStrokeWidth() {
  const v = Number(strokeRange?.value ?? 50);
  return (v / 50) * DEMO_BASE_STROKE;
}

function applyDemoStroke(svg, canonicalWidth) {
  if (!svg) return;
  const w = Number(canonicalWidth);
  const groups = svg.querySelectorAll("g[stroke]");
  groups.forEach((g) => {
    const stroke = g.getAttribute("stroke");
    if (!stroke || stroke.toLowerCase() === "none") return;
    if (!Number.isFinite(w) || w <= 0) {
      g.setAttribute("stroke-width", "0");
    } else {
      g.setAttribute("stroke-width", String(w));
    }
  });
}

/** Preview-only modulation: stroke cosmetics + subtle SVG displacement ("curvy"). Topology unchanged. */
function ensureCurvyDisplacementFilter(svg) {
  let defs = svg.querySelector("defs");
  if (!defs) {
    defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    svg.insertBefore(defs, svg.firstChild);
  }
  if (defs.querySelector("#monotileDemoCurvyFilter")) return;

  const filter = document.createElementNS("http://www.w3.org/2000/svg", "filter");
  filter.setAttribute("id", "monotileDemoCurvyFilter");
  filter.setAttribute("x", "-50%");
  filter.setAttribute("y", "-50%");
  filter.setAttribute("width", "200%");
  filter.setAttribute("height", "200%");

  const turb = document.createElementNS("http://www.w3.org/2000/svg", "feTurbulence");
  turb.setAttribute("type", "fractalNoise");
  turb.setAttribute("baseFrequency", "0.045");
  turb.setAttribute("numOctaves", "1");
  turb.setAttribute("seed", "2");
  turb.setAttribute("result", "noise");

  const disp = document.createElementNS("http://www.w3.org/2000/svg", "feDisplacementMap");
  disp.setAttribute("in", "SourceGraphic");
  disp.setAttribute("in2", "noise");
  disp.setAttribute("scale", "0");
  disp.setAttribute("xChannelSelector", "R");
  disp.setAttribute("yChannelSelector", "G");

  filter.appendChild(turb);
  filter.appendChild(disp);
  defs.appendChild(filter);
}

function syncCurvyDisplacement(svg, enabled) {
  const disp = svg.querySelector("#monotileDemoCurvyFilter feDisplacementMap");
  if (!disp) return;
  disp.setAttribute("scale", enabled ? "0.45" : "0");
}

function applyOutlineStyle(svg) {
  if (!svg || !outlineStyleSelect) return;
  const mode = outlineStyleSelect.value ?? "flat";
  ensureCurvyDisplacementFilter(svg);

  svg.querySelectorAll("g[stroke]").forEach((g) => {
    const stroke = g.getAttribute("stroke");
    if (!stroke || stroke.toLowerCase() === "none") return;

    switch (mode) {
      case "curvy":
        g.setAttribute("stroke-linejoin", "round");
        g.setAttribute("stroke-linecap", "round");
        g.setAttribute("stroke-miterlimit", "10");
        break;
      case "spiky":
        g.setAttribute("stroke-linejoin", "miter");
        g.setAttribute("stroke-linecap", "butt");
        g.setAttribute("stroke-miterlimit", "1.12");
        break;
      case "flat":
      default:
        g.setAttribute("stroke-linejoin", "miter");
        g.setAttribute("stroke-linecap", "square");
        g.setAttribute("stroke-miterlimit", "8");
        break;
    }
  });

  syncCurvyDisplacement(svg, mode === "curvy");
  svg.style.filter = mode === "curvy" ? "url(#monotileDemoCurvyFilter)" : "";
}

async function fetchSvgMarkup(url) {
  if (svgTextCache.has(url)) return svgTextCache.get(url);
  const response = await fetch(url, {cache: "force-cache"});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const text = await response.text();
  svgTextCache.set(url, text);
  return text;
}

async function updateDemo() {
  const preset = currentPreset();
  renderStats(preset);
  if (!demoSvgHost) return;
  demoSvgHost.innerHTML = '<p class="demo-loading">Loading preview…</p>';
  try {
    const markup = await fetchSvgMarkup(preset.src);
    demoSvgHost.innerHTML = markup;
    const svg = demoSvgHost.querySelector("svg");
    if (!svg) throw new Error("Markup did not contain an <svg>");
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("aria-label", preset.alt);

    applyOutlineStyle(svg);
    applyDemoStroke(svg, computeCanonicalStrokeWidth());
  } catch (err) {
    demoSvgHost.innerHTML = '<p class="demo-error">Could not load this example SVG.</p>';
    console.error(err);
  }
}

function updateDisplay() {
  if (previewFrame && previewMagnifyRange) {
    previewFrame.style.setProperty("--tile-scale", String(Number(previewMagnifyRange.value) / 100));
  }
  const svg = demoSvgHost?.querySelector("svg");
  if (svg && outlineStyleSelect) applyOutlineStyle(svg);
  applyDemoStroke(svg, computeCanonicalStrokeWidth());
}

if (
  presetSelect &&
  outlineStyleSelect &&
  previewMagnifyRange &&
  strokeRange &&
  demoSvgHost &&
  demoStats &&
  previewFrame
) {
  presetSelect.addEventListener("change", () => void updateDemo());
  outlineStyleSelect.addEventListener("change", () => updateDisplay());
  outlineStyleSelect.addEventListener("input", () => updateDisplay());
  previewMagnifyRange.addEventListener("input", updateDisplay);
  strokeRange.addEventListener("input", updateDisplay);

  void updateDemo();
  updateDisplay();
}

async function startCheckout() {
  const email = window.prompt("Email for your Studio API key:");
  if (!email) return;
  if (checkoutStatus) checkoutStatus.textContent = "Opening secure checkout...";
  try {
    const response = await fetch(`${apiBase}/v1/billing/checkout`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({email})
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Checkout unavailable (${response.status})`);
    }
    const payload = await response.json();
    window.location.href = payload.checkout_url;
  } catch (err) {
    if (checkoutStatus) {
      checkoutStatus.textContent =
        "Checkout is not enabled yet. The live API and manual API-key tiers are ready; connect Stripe to turn this button on.";
    }
    console.error(err);
  }
}

for (const button of checkoutButtons) {
  button.addEventListener("click", startCheckout);
}

if (leadForm) {
  leadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(leadForm);
    if (checkoutStatus) checkoutStatus.textContent = "Saving your request...";
    try {
      const response = await fetch(`${apiBase}/v1/leads`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          email: data.get("email"),
          use_case: data.get("use_case"),
          source: "homepage"
        })
      });
      if (!response.ok) throw new Error(await response.text());
      leadForm.reset();
      if (checkoutStatus) checkoutStatus.textContent = "You're on the launch list. We'll use this to prioritize demos and access.";
    } catch (err) {
      if (checkoutStatus) checkoutStatus.textContent = "Could not save that yet. Try again in a moment.";
      console.error(err);
    }
  });
}
