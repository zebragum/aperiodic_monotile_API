const demoPresets = [
  {
    id: "circle-100u",
    kind: "svg",
    src: "assets/examples/circle-100u.svg",
    alt: "A circular aperiodic monotile patch",
    shape: "Circle",
    unit: "100-unit diameter",
    tiles: "~1,036 tiles",
    format: "SVG",
  },
  {
    id: "rect-9x4",
    kind: "svg",
    src: "assets/examples/rectangle-9x4.svg",
    alt: "A rectangular aperiodic monotile patch",
    shape: "Rectangle",
    unit: "90 x 40 units",
    tiles: "~500 tiles",
    format: "PNG",
  },
  {
    id: "tri-50u",
    kind: "svg",
    src: "assets/examples/triangle-50u.svg",
    alt: "An equilateral triangular aperiodic monotile patch",
    shape: "Triangle",
    unit: "50-unit edge",
    tiles: "~166 tiles",
    format: "JPG",
  },
  {
    id: "stl-panel",
    kind: "model",
    src: "assets/examples/rectangle-9x4.svg",
    alt: "A flat STL-style aperiodic tiling panel with raised linework",
    shape: "Fabrication panel",
    unit: "90 x 40 units",
    tiles: "~500 tiles",
    format: "STL",
  },
  {
    id: "glb-game",
    kind: "model",
    src: "assets/examples/triangle-50u.svg",
    alt: "A GLB-style field of independently selectable monotile objects",
    shape: "Game-ready tile field",
    unit: "50-unit edge",
    tiles: "~166 tiles",
    format: "GLB",
  },
];

const presetSelect = document.querySelector("#presetSelect");
const demoSvgHost = document.querySelector("#demoSvgHost");
const demoStats = document.querySelector("#demoStats");
const checkoutEmail = document.querySelector("#checkoutEmail");
const checkoutStatus = document.querySelector("#checkoutStatus");

const svgTextCache = new Map();
const apiBase = "https://aperiodic-monotile-api.onrender.com";

function currentPreset() {
  const id = presetSelect?.value ?? demoPresets[0].id;
  const found = demoPresets.find((p) => p.id === id);
  return found ?? demoPresets[0];
}

function renderStats(example) {
  if (!demoStats) return;
  const rows = [
    ["Shape", example.shape],
    ["Unit", example.unit],
    ["Tiles", example.tiles],
    ["Format", example.format],
  ];
  demoStats.replaceChildren(
    ...rows.map(([label, value]) => {
      const row = document.createElement("span");
      const key = document.createElement("strong");
      key.textContent = `${label}: `;
      row.append(key, document.createTextNode(value));
      return row;
    }),
  );
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

function attachDragRotation(stage) {
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let rotX = 62;
  let rotZ = -22;

  const apply = () => {
    stage.style.setProperty("--rx", `${rotX}deg`);
    stage.style.setProperty("--rz", `${rotZ}deg`);
  };
  apply();

  stage.addEventListener("pointerdown", (event) => {
    dragging = true;
    startX = event.clientX;
    startY = event.clientY;
    stage.setPointerCapture(event.pointerId);
    stage.classList.add("is-dragging");
  });
  stage.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const dx = event.clientX - startX;
    const dy = event.clientY - startY;
    startX = event.clientX;
    startY = event.clientY;
    rotZ += dx * 0.28;
    rotX = Math.max(28, Math.min(78, rotX - dy * 0.18));
    apply();
  });
  const stop = (event) => {
    dragging = false;
    stage.classList.remove("is-dragging");
    if (stage.hasPointerCapture(event.pointerId)) {
      stage.releasePointerCapture(event.pointerId);
    }
  };
  stage.addEventListener("pointerup", stop);
  stage.addEventListener("pointercancel", stop);
}

function modelPreview(example, svg) {
  const scene = document.createElement("div");
  scene.className = `model-preview model-preview--${example.format.toLowerCase()}`;
  scene.setAttribute("role", "img");
  scene.setAttribute("aria-label", example.alt);

  const stage = document.createElement("div");
  stage.className = "spectre-3d-stage";
  stage.tabIndex = 0;
  stage.title = "Drag to rotate this aperiodic monotile preview";
  attachDragRotation(stage);

  const slab = document.createElement("div");
  slab.className = "spectre-3d-slab";
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  svg.setAttribute("aria-hidden", "true");

  const depthLayers = 4;
  for (let i = depthLayers; i >= 1; i -= 1) {
    const layer = svg.cloneNode(true);
    layer.classList.add("spectre-3d-depth-layer");
    layer.style.setProperty("--layer", String(i));
    slab.append(layer);
  }
  svg.classList.add("spectre-3d-top");
  slab.append(svg);
  stage.append(slab);

  const caption = document.createElement("p");
  caption.textContent =
    example.format === "GLB"
      ? "Drag to rotate. Production GLB exports one named 3D object per tile, one unit deep by default."
      : "Drag to rotate. Production STL exports matching one-unit-deep extruded linework by default.";
  scene.append(stage, caption);
  return scene;
}

async function loadPresetSvg(preset) {
  const markup = await fetchSvgMarkup(preset.src);
  const svg = safeSvgFromMarkup(markup);
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  svg.setAttribute("aria-label", preset.alt);
  return svg;
}

async function updateDemo() {
  const preset = currentPreset();
  renderStats(preset);
  if (!demoSvgHost) return;

  demoSvgHost.replaceChildren(statusNode("demo-loading", "Loading preview..."));
  try {
    const svg = await loadPresetSvg(preset);
    demoSvgHost.replaceChildren(preset.kind === "model" ? modelPreview(preset, svg) : svg);
  } catch (err) {
    demoSvgHost.replaceChildren(statusNode("demo-error", "Could not load this example."));
    console.error(err);
  }
}

if (
  presetSelect &&
  demoSvgHost &&
  demoStats
) {
  presetSelect.addEventListener("change", () => void updateDemo());

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
