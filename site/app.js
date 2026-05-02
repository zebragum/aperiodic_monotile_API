const examples = {
  circle: {
    src: "assets/examples/circle-100u.svg",
    alt: "A 100-unit circular Spectre monotile patch",
    shape: "Circle",
    units: "100 units wide",
    pixels: "1000px preview",
    tiles: "1,036 tiles",
    formats: "SVG now; CSV/JSON/STL/glTF via API"
  },
  rectangle: {
    src: "assets/examples/rectangle-9x4.svg",
    alt: "A 9:4 rectangular Spectre monotile patch",
    shape: "Rectangle",
    units: "90 x 40 units",
    pixels: "9:4 aspect",
    tiles: "500 tiles",
    formats: "SVG now; CSV/JSON/STL/glTF via API"
  },
  triangle: {
    src: "assets/examples/triangle-50u.svg",
    alt: "A 50-unit equilateral triangular Spectre monotile patch",
    shape: "Triangle",
    units: "50-unit side",
    pixels: "500px preview",
    tiles: "166 tiles",
    formats: "SVG now; CSV/JSON/STL/glTF via API"
  }
};

const shapeSelect = document.querySelector("#shapeSelect");
const tileScaleRange = document.querySelector("#tileScaleRange");
const strokeRange = document.querySelector("#strokeRange");
const demoSvgHost = document.querySelector("#demoSvgHost");
const demoStats = document.querySelector("#demoStats");
const previewFrame = document.querySelector(".preview-frame");

/** Example SVGs encode outlines at stroke-width 0.25 in canonical units. */
const DEMO_BASE_STROKE = 0.25;
const svgTextCache = new Map();
const checkoutButtons = [document.querySelector("#studioCheckout"), document.querySelector("#ctaCheckout")].filter(Boolean);
const checkoutStatus = document.querySelector("#checkoutStatus");
const leadForm = document.querySelector("#leadForm");
const apiBase = "https://aperiodic-monotile-api.onrender.com";

function renderStats(example) {
  if (!demoStats) return;
  demoStats.innerHTML = `
    <strong>${example.shape}</strong>
    <span>${example.units}</span>
    <span>${example.pixels}</span>
    <span>${example.tiles}</span>
    <span>${example.formats}</span>
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

async function fetchSvgMarkup(url) {
  if (svgTextCache.has(url)) return svgTextCache.get(url);
  const response = await fetch(url, {cache: "force-cache"});
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const text = await response.text();
  svgTextCache.set(url, text);
  return text;
}

async function updateDemo() {
  const example = examples[shapeSelect.value];
  renderStats(example);
  if (!demoSvgHost) return;
  demoSvgHost.innerHTML = "<p class=\"demo-loading\">Loading preview…</p>";
  try {
    const markup = await fetchSvgMarkup(example.src);
    demoSvgHost.innerHTML = markup;
    const svg = demoSvgHost.querySelector("svg");
    if (!svg) throw new Error("Markup did not contain an <svg>");
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("aria-label", example.alt);
    applyDemoStroke(svg, computeCanonicalStrokeWidth());
  } catch (err) {
    demoSvgHost.innerHTML = "<p class=\"demo-error\">Could not load this example SVG.</p>";
    console.error(err);
  }
}

function updateDisplay() {
  if (previewFrame && tileScaleRange) {
    previewFrame.style.setProperty("--tile-scale", String(Number(tileScaleRange.value) / 100));
  }
  const svg = demoSvgHost?.querySelector("svg");
  applyDemoStroke(svg, computeCanonicalStrokeWidth());
}

if (shapeSelect && tileScaleRange && strokeRange && demoSvgHost && demoStats && previewFrame) {
  shapeSelect.addEventListener("change", () => void updateDemo());
  tileScaleRange.addEventListener("input", updateDisplay);
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
