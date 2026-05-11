const demoPresets = [
  {
    id: "circle-100u",
    src: "assets/examples/circle-100u.svg",
    alt: "A circular Spectre / Tile(1,1) monotile patch",
    headline: "Circle mask",
    extent: "~100-unit diameter · circle clip",
    approxTiles: "~1,036 tiles",
    rasterNote: "~1000px SVG canvas",
    formatsHint: "Pre-cached SVG; regenerate any extent via API",
  },
  {
    id: "rect-9x4",
    src: "assets/examples/rectangle-9x4.svg",
    alt: "A rectangular Spectre monotile patch",
    headline: "9∶4 rectangle",
    extent: "90 × 40 canonical units · axis-aligned rectangle",
    approxTiles: "~500 tiles",
    rasterNote: "900×400 SVG canvas",
    formatsHint: "Pre-cached SVG; regenerate via API",
  },
  {
    id: "tri-50u",
    src: "assets/examples/triangle-50u.svg",
    alt: "An equilateral triangular Spectre monotile patch",
    headline: "Equilateral triangle",
    extent: "50-unit edges · centroid-centered mask",
    approxTiles: "~166 tiles",
    rasterNote: "500×433 SVG canvas",
    formatsHint: "Pre-cached SVG; regenerate via API",
  },
];

const presetSelect = document.querySelector("#presetSelect");
const strokeRange = document.querySelector("#strokeRange");
const demoSvgHost = document.querySelector("#demoSvgHost");
const demoStats = document.querySelector("#demoStats");
const checkoutEmail = document.querySelector("#checkoutEmail");
const checkoutStatus = document.querySelector("#checkoutStatus");

/** Example SVGs ship with strokes at stroke-width 0.25 in canonical units. */
const DEMO_BASE_STROKE = 0.25;
const svgTextCache = new Map();
const apiBase = "https://aperiodic-monotile-api.onrender.com";

function currentPreset() {
  const id = presetSelect?.value ?? demoPresets[0].id;
  const found = demoPresets.find((p) => p.id === id);
  return found ?? demoPresets[0];
}

function renderStats(example) {
  if (!demoStats) return;
  demoStats.replaceChildren(
    Object.assign(document.createElement("strong"), { textContent: example.headline }),
    Object.assign(document.createElement("span"), { textContent: example.extent }),
    Object.assign(document.createElement("span"), { textContent: example.approxTiles }),
    Object.assign(document.createElement("span"), { textContent: example.rasterNote }),
    Object.assign(document.createElement("span"), { textContent: example.formatsHint }),
  );
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

async function fetchSvgMarkup(url) {
  if (svgTextCache.has(url)) return svgTextCache.get(url);
  const response = await fetch(url, { cache: "force-cache" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const text = await response.text();
  svgTextCache.set(url, text);
  return text;
}

function statusNode(className, text) {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = text;
  return p;
}

function safeSvgFromMarkup(markup) {
  const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
  const parserError = doc.querySelector("parsererror");
  if (parserError) throw new Error("Could not parse SVG preview");

  const svg = doc.documentElement;
  if (!svg || svg.tagName.toLowerCase() !== "svg") {
    throw new Error("Markup did not contain an <svg>");
  }

  // These previews are bundled first-party assets. Keep this guard anyway so
  // future API-loaded SVGs cannot execute script in the page context.
  svg.querySelectorAll("script, foreignObject, iframe, object, embed").forEach((node) => node.remove());
  svg.querySelectorAll("*").forEach((node) => {
    for (const attr of Array.from(node.attributes)) {
      const name = attr.name.toLowerCase();
      const value = attr.value.trim().toLowerCase();
      if (name.startsWith("on") || value.startsWith("javascript:")) {
        node.removeAttribute(attr.name);
      }
    }
  });
  return document.importNode(svg, true);
}

async function updateDemo() {
  const preset = currentPreset();
  renderStats(preset);
  if (!demoSvgHost) return;
  demoSvgHost.replaceChildren(statusNode("demo-loading", "Loading preview..."));
  try {
    const markup = await fetchSvgMarkup(preset.src);
    const svg = safeSvgFromMarkup(markup);
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("aria-label", preset.alt);

    applyDemoStroke(svg, computeCanonicalStrokeWidth());
    demoSvgHost.replaceChildren(svg);
  } catch (err) {
    demoSvgHost.replaceChildren(statusNode("demo-error", "Could not load this example SVG."));
    console.error(err);
  }
}

function updateDisplay() {
  const svg = demoSvgHost?.querySelector("svg");
  applyDemoStroke(svg, computeCanonicalStrokeWidth());
}

if (
  presetSelect &&
  strokeRange &&
  demoSvgHost &&
  demoStats
) {
  presetSelect.addEventListener("change", () => void updateDemo());
  strokeRange.addEventListener("input", updateDisplay);

  void updateDemo();
}

/**
 * Stripe Checkout — pass plan slug understood by POST /v1/billing/checkout
 * (day_pass, solo_monthly, solo_yearly, teams_monthly, teams_yearly).
 */
async function startBillingCheckout(planSlug) {
  const email = checkoutEmail?.value?.trim() ?? "";
  if (!email) {
    if (checkoutStatus) checkoutStatus.textContent = "Enter an email address first.";
    checkoutEmail?.focus();
    return;
  }
  if (checkoutStatus) checkoutStatus.textContent = "Starting secure checkout...";
  try {
    const response = await fetch(`${apiBase}/v1/billing/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email.trim(),
        plan: planSlug,
      }),
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
        "Billing could not start. Checkout may still be configuring. Please try again shortly.";
    }
    console.error(err);
  }
}

for (const button of document.querySelectorAll("[data-checkout-plan]")) {
  button.addEventListener("click", () => {
    const plan = button.getAttribute("data-checkout-plan");
    if (plan) void startBillingCheckout(plan);
  });
}
