const demoPresets = [
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
    shape: "Raised 3D panel",
    unit: "90 x 40 units",
    tiles: "~500 tiles",
    format: "STL",
  },
  {
    id: "glb-game",
    kind: "model",
    src: "assets/examples/square-50u.svg",
    alt: "A square GLB-style field of independently selectable monotile objects",
    shape: "Game-ready square tile field",
    unit: "50 x 50 units",
    tiles: "~352 tiles",
    format: "GLB",
  },
];

const presetSelect = document.querySelector("#presetSelect");
const demoSvgHost = document.querySelector("#demoSvgHost");
const checkoutStatus = document.querySelector("#checkoutStatus");

const svgTextCache = new Map();
const apiBase = "https://aperiodic-monotile-api.onrender.com";
const analyticsVisitorKey = "monotile.analytics.visitor.v1";
const analyticsSessionKey = "monotile.analytics.session.v1";
const generatorTileDataUrl = "assets/samples/sample-tiles.json";
const spectreProtoRing = [
  [0, 0],
  [1, 0],
  [1.5, -0.8660254],
  [2.3660254, -0.3660254],
  [2.3660254, 0.6339746],
  [3.3660254, 0.6339746],
  [3.8660254, 1.5],
  [3, 2],
  [2.1339746, 1.5],
  [1.6339746, 2.3660254],
  [0.6339746, 2.3660254],
  [-0.3660254, 2.3660254],
  [-0.8660254, 1.5],
  [0, 1],
];
const defaultGeneratorPalette = [
  { color: "#8f2f13", transparent: false },
  { color: "#b74619", transparent: false },
  { color: "#d95a24", transparent: false },
  { color: "#f07048", transparent: false },
  { color: "#ff875e", transparent: false },
  { color: "#ffa05f", transparent: false },
  { color: "#ffb85f", transparent: false },
  { color: "#f4c86a", transparent: false },
  { color: "#ffd166", transparent: false },
];
const palettePresets = [
  ["#ff6a4a", "#ffd166", "#52b885", "#3d7ab7", "#a431aa", "#cbce42", "#57c9ce", "#f7efe8", "#000000"],
  ["#0f172a", "#38bdf8", "#a78bfa", "#f472b6", "#fb7185", "#facc15", "#4ade80", "#e2e8f0", "#000000"],
  ["#1b1b1b", "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#000000"],
  ["#f8fafc", "#bae6fd", "#bfdbfe", "#ddd6fe", "#fecdd3", "#fed7aa", "#fef08a", "#bbf7d0", "#000000"],
];

const generatorShape = document.querySelector("#generatorShape");
const generatorScale = document.querySelector("#generatorScale");
const generatorScaleValue = document.querySelector("#generatorScaleValue");
const generatorCanvas = document.querySelector("#generatorCanvas");
const paletteGrid = document.querySelector("#paletteGrid");
const randomizePaletteButton = document.querySelector("#randomizePalette");
const downloadPngButton = document.querySelector("#downloadPng");
const downloadJpgButton = document.querySelector("#downloadJpg");
const generatorStatus = document.querySelector("#generatorStatus");
const generatorSummary = document.querySelector("#generatorSummary");

function randomAnalyticsId(prefix) {
  if (window.crypto?.randomUUID) return `${prefix}_${window.crypto.randomUUID()}`;
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

function storedAnalyticsId(key, prefix, storage) {
  try {
    const existing = storage.getItem(key);
    if (existing) return existing;
    const fresh = randomAnalyticsId(prefix);
    storage.setItem(key, fresh);
    return fresh;
  } catch (_) {
    return randomAnalyticsId(prefix);
  }
}

function analyticsVisitorId() {
  return storedAnalyticsId(analyticsVisitorKey, "visitor", window.localStorage);
}

function analyticsSessionId() {
  return storedAnalyticsId(analyticsSessionKey, "session", window.sessionStorage);
}

function trackLaunchEvent(eventName, payload = {}) {
  const body = {
    event_name: eventName,
    source: "website",
    visitor_id: analyticsVisitorId(),
    session_id: analyticsSessionId(),
    page_url: window.location.href,
    referrer: document.referrer || "",
    user_agent: navigator.userAgent,
    ...payload,
  };
  const json = JSON.stringify(body);
  if (navigator.sendBeacon) {
    const blob = new Blob([json], { type: "application/json" });
    if (navigator.sendBeacon(`${apiBase}/v1/analytics/events`, blob)) return;
  }
  fetch(`${apiBase}/v1/analytics/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: json,
    keepalive: true,
  }).catch(() => {
    // Analytics must never block downloads or checkout.
  });
}

function clonePalette(palette) {
  return palette.map((slot) => ({ ...slot }));
}

let generatorPalette = clonePalette(defaultGeneratorPalette);
let generatorTiles = [];
let generatorBounds = null;

function applyAffine(affine6, points) {
  const [a, b, c, d, e, f] = affine6;
  return points.map(([x, y]) => [a * x + b * y + c, d * x + e * y + f]);
}

function tileBounds(tiles) {
  const xs = [];
  const ys = [];
  for (const tile of tiles) {
    for (const [x, y] of tile.ring) {
      xs.push(x);
      ys.push(y);
    }
  }
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

function tilePaletteIndex(tile) {
  const source = `${tile.label}:${tile.id}`;
  let hash = 0;
  for (let i = 0; i < source.length; i += 1) {
    hash = (hash * 31 + source.charCodeAt(i)) >>> 0;
  }
  return hash % generatorPalette.length;
}

function hexToRgb(hex) {
  const normalized = hex.replace("#", "").trim();
  const value = Number.parseInt(normalized.length === 3
    ? normalized.split("").map((ch) => ch + ch).join("")
    : normalized, 16);
  if (Number.isNaN(value)) return [255, 255, 255];
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function darkenHex(hex, factor = 0.62) {
  const [r, g, b] = hexToRgb(hex);
  return `rgb(${Math.round(r * factor)}, ${Math.round(g * factor)}, ${Math.round(b * factor)})`;
}

function createShapePath(ctx, shape, x, y, width, height) {
  const cx = x + width / 2;
  const cy = y + height / 2;
  ctx.beginPath();
  if (shape === "circle") {
    const radius = Math.min(width, height) * 0.47;
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  } else if (shape === "triangle") {
    const radius = Math.min(width, height) * 0.56;
    ctx.moveTo(cx, cy - radius);
    ctx.lineTo(cx + radius * 0.95, cy + radius * 0.72);
    ctx.lineTo(cx - radius * 0.95, cy + radius * 0.72);
    ctx.closePath();
  } else if (shape === "hexagon") {
    const radius = Math.min(width, height) * 0.48;
    for (let i = 0; i < 6; i += 1) {
      const angle = Math.PI / 6 + i * Math.PI / 3;
      const px = cx + Math.cos(angle) * radius;
      const py = cy + Math.sin(angle) * radius;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
  } else if (shape === "rounded_rect") {
    const radius = Math.min(width, height) * 0.14;
    if (ctx.roundRect) {
      ctx.roundRect(x, y, width, height, radius);
    } else {
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + width - radius, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
      ctx.lineTo(x + width, y + height - radius);
      ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
      ctx.lineTo(x + radius, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
    }
  } else {
    ctx.rect(x, y, width, height);
  }
}

function renderGenerator() {
  if (!generatorCanvas || !generatorTiles.length || !generatorBounds) return;
  const ctx = generatorCanvas.getContext("2d");
  const width = generatorCanvas.width;
  const height = generatorCanvas.height;
  const shape = generatorShape?.value || "rectangle";
  const scaleValue = Number.parseFloat(generatorScale?.value || "0.9");
  if (generatorScaleValue) generatorScaleValue.textContent = scaleValue.toFixed(2);
  if (generatorSummary) {
    const shapeLabel = shape.replace("_", " ");
    generatorSummary.textContent = `${shapeLabel} · ${scaleValue.toFixed(2)}x · PNG/JPG free`;
  }

  ctx.clearRect(0, 0, width, height);

  const pad = 58;
  const clipX = pad;
  const clipY = pad;
  const clipW = width - pad * 2;
  const clipH = height - pad * 2;
  const targetWorldW = 90;
  const targetWorldH = 40;
  const baseScale = Math.min(clipW / targetWorldW, clipH / targetWorldH) * 0.98;
  const renderScale = baseScale * scaleValue;
  const cx = (generatorBounds.minX + generatorBounds.maxX) / 2;
  const cy = (generatorBounds.minY + generatorBounds.maxY) / 2;
  const toScreen = ([x, y]) => [
    width / 2 + (x - cx) * renderScale,
    height / 2 - (y - cy) * renderScale,
  ];

  ctx.save();
  createShapePath(ctx, shape, clipX, clipY, clipW, clipH);
  ctx.clip();

  for (const tile of generatorTiles) {
    const paletteSlot = generatorPalette[tilePaletteIndex(tile)];
    const points = tile.ring.map((point) => toScreen(point));
    ctx.beginPath();
    points.forEach(([x, y], index) => {
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.lineWidth = Math.max(0.75, renderScale * 0.035);
    ctx.strokeStyle = paletteSlot.transparent ? "rgba(255,255,255,0.28)" : darkenHex(paletteSlot.color);
    if (!paletteSlot.transparent) {
      ctx.fillStyle = paletteSlot.color;
      ctx.fill();
    }
    ctx.stroke();
  }
  ctx.restore();

}

function renderPaletteControls() {
  if (!paletteGrid) return;
  paletteGrid.replaceChildren();
  generatorPalette.forEach((slot, index) => {
    const item = document.createElement("div");
    item.className = "palette-slot";

    const label = document.createElement("span");
    label.textContent = String(index + 1);

    const color = document.createElement("input");
    color.type = "color";
    color.value = slot.color;
    color.setAttribute("aria-label", `Palette color ${index + 1}`);
    color.addEventListener("input", () => {
      generatorPalette[index].color = color.value;
      renderGenerator();
    });

    const transparentLabel = document.createElement("label");
    transparentLabel.className = "palette-transparent";
    transparentLabel.title = "Transparent";
    const transparent = document.createElement("input");
    transparent.type = "checkbox";
    transparent.checked = slot.transparent;
    transparent.addEventListener("change", () => {
      generatorPalette[index].transparent = transparent.checked;
      item.classList.toggle("is-transparent", transparent.checked);
      renderGenerator();
    });
    transparentLabel.append(transparent, document.createTextNode("Transparent"));

    item.classList.toggle("is-transparent", slot.transparent);
    item.append(label, color, transparentLabel);
    paletteGrid.append(item);
  });
}

async function loadGeneratorTiles() {
  const response = await fetch(generatorTileDataUrl, { cache: "force-cache" });
  if (!response.ok) throw new Error(`Could not load generator data (${response.status})`);
  const payload = await response.json();
  generatorTiles = payload.tiles.map((tile) => ({
    id: tile.id || "",
    label: tile.label || "",
    ring: applyAffine(tile.generator_affine6, spectreProtoRing),
  }));
  generatorBounds = tileBounds(generatorTiles);
}

function downloadCanvas(kind) {
  if (!generatorCanvas) return;
  const source = generatorCanvas;
  const canvas = document.createElement("canvas");
  canvas.width = source.width;
  canvas.height = source.height;
  const ctx = canvas.getContext("2d");
  if (kind === "jpg") {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  ctx.drawImage(source, 0, 0);
  const mime = kind === "jpg" ? "image/jpeg" : "image/png";
  const filename = `aperiodic-monotile-preview.${kind}`;
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    if (generatorStatus) {
      generatorStatus.textContent = `Downloaded ${filename}. Upgrade for SVG, GLB, STL, CSV, or JSON.`;
    }
    trackLaunchEvent("sample_download", {
      sample_file: filename,
      metadata: { source: "free_generator", kind },
    });
  }, mime, kind === "jpg" ? 0.92 : undefined);
}

async function initGenerator() {
  if (!generatorCanvas) return;
  if (generatorShape) generatorShape.value = "rectangle";
  renderPaletteControls();
  try {
    await loadGeneratorTiles();
    renderGenerator();
  } catch (err) {
    console.error(err);
    if (generatorStatus) generatorStatus.textContent = "Could not load the free generator data.";
  }
  generatorShape?.addEventListener("change", renderGenerator);
  generatorScale?.addEventListener("input", renderGenerator);
  randomizePaletteButton?.addEventListener("click", () => {
    const preset = palettePresets[Math.floor(Math.random() * palettePresets.length)];
    generatorPalette = preset.map((color, index) => ({
      color,
      transparent: index === preset.length - 1,
    }));
    renderPaletteControls();
    renderGenerator();
  });
  downloadPngButton?.addEventListener("click", () => downloadCanvas("png"));
  downloadJpgButton?.addEventListener("click", () => downloadCanvas("jpg"));
  document.querySelectorAll("[data-upgrade-format]").forEach((button) => {
    button.addEventListener("click", () => {
      const format = button.getAttribute("data-upgrade-format")?.toUpperCase() || "production";
      if (generatorStatus) {
        generatorStatus.textContent = `${format} exports are paid production geometry. Start with a Day Pass or Solo plan below.`;
      }
      trackLaunchEvent("requested_format", {
        format: format.toLowerCase(),
        metadata: { source: "free_generator_upgrade_prompt" },
      });
      document.querySelector("#pricing")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function currentPreset() {
  const id = presetSelect?.value ?? demoPresets[0].id;
  const found = demoPresets.find((p) => p.id === id);
  return found ?? demoPresets[0];
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

function imagePreview(example) {
  const img = document.createElement("img");
  img.src = example.src;
  img.alt = example.alt;
  img.loading = "eager";
  img.decoding = "async";
  return img;
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
  if (!demoSvgHost) return;

  demoSvgHost.replaceChildren(statusNode("demo-loading", "Loading preview..."));
  try {
    const svg = await loadPresetSvg(preset);
    demoSvgHost.replaceChildren(preset.kind === "model" ? modelPreview(preset, svg) : svg);
  } catch (err) {
    demoSvgHost.replaceChildren(imagePreview(preset));
    console.error(err);
  }
}

if (
  presetSelect &&
  demoSvgHost
) {
  presetSelect.addEventListener("change", () => void updateDemo());

  void updateDemo();
}

void initGenerator();

for (const link of document.querySelectorAll(".sample-downloads a[download]")) {
  link.addEventListener("click", () => {
    trackLaunchEvent("sample_download", {
      sample_file: link.getAttribute("href") || link.textContent || "unknown",
      metadata: {
        label: link.textContent?.trim() || "",
        download: link.getAttribute("download") || "",
      },
    });
  });
}

/**
 * Stripe Checkout — pass plan slug understood by POST /v1/billing/checkout
 * (day_pass, solo_monthly, solo_yearly, teams_monthly, teams_yearly).
 */
function emailLooksValid(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function removeOtherCheckoutForms(activeCard) {
  document.querySelectorAll(".checkout-inline").forEach((form) => {
    if (!activeCard || !activeCard.contains(form)) form.remove();
  });
}

function ensureCheckoutForm(button, planSlug) {
  const card = button.closest(".price-card");
  if (!card) return null;
  removeOtherCheckoutForms(card);

  const existing = card.querySelector(".checkout-inline");
  if (existing) return existing;

  const form = document.createElement("form");
  form.className = "checkout-inline";
  form.noValidate = true;

  const label = document.createElement("label");
  const labelText = document.createElement("span");
  labelText.textContent = "Email for checkout receipt and API-key delivery";
  const input = document.createElement("input");
  input.type = "email";
  input.name = "email";
  input.autocomplete = "email";
  input.placeholder = "you@example.com";
  input.required = true;
  label.append(labelText, input);

  const status = document.createElement("p");
  status.className = "checkout-inline-status";
  status.setAttribute("aria-live", "polite");

  const submit = document.createElement("button");
  submit.className = "button full";
  submit.type = "submit";
  submit.textContent = "Continue to secure checkout";

  form.append(label, submit, status);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void startBillingCheckout(planSlug, button);
  });

  const actions = button.closest(".pricing-actions");
  if (actions) {
    actions.insertAdjacentElement("afterend", form);
  } else {
    card.append(form);
  }
  return form;
}

async function startBillingCheckout(planSlug, button) {
  const form = button ? ensureCheckoutForm(button, planSlug) : null;
  const emailInput = form?.querySelector('input[type="email"]');
  const inlineStatus = form?.querySelector(".checkout-inline-status");
  const submit = form?.querySelector('button[type="submit"]');
  const email = emailInput?.value?.trim() ?? "";

  if (!form || !email) {
    if (inlineStatus) inlineStatus.textContent = "Enter an email address to continue.";
    if (checkoutStatus) checkoutStatus.textContent = "";
    emailInput?.focus();
    return;
  }
  if (!emailLooksValid(email)) {
    if (inlineStatus) inlineStatus.textContent = "Enter a valid email address.";
    emailInput.focus();
    return;
  }
  if (checkoutStatus) checkoutStatus.textContent = "Starting secure checkout...";
  if (inlineStatus) inlineStatus.textContent = "Starting secure checkout...";
  if (submit) submit.disabled = true;
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
    if (submit) submit.disabled = false;
    if (inlineStatus) {
      inlineStatus.textContent =
        "Billing could not start. Please try again shortly.";
    }
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
    if (plan) void startBillingCheckout(plan, button);
  });
}
