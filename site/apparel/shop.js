const apiBase = window.SITE_CONFIG?.apiBase || "https://api.untiling.com";
const apiFallbackBases = window.SITE_CONFIG?.apiFallbacks || [
  "https://api.aperiodicgenerator.com",
  "https://aperiodic-monotile-api.onrender.com",
];
const cartStorageKey = "monotile.shop.cart.v1";

const shopStatus = document.querySelector("#shopStatus");
const productGrid = document.querySelector("#productGrid");
const cartOpenButton = document.querySelector("#cartOpen");
const cartCloseButton = document.querySelector("#cartClose");
const cartOverlay = document.querySelector("#cartOverlay");
const cartItemsHost = document.querySelector("#cartItems");
const cartCountBadge = document.querySelector("#cartCount");
const cartSubtotalNode = document.querySelector("#cartSubtotal");
const checkoutButton = document.querySelector("#checkoutButton");
const cartStatus = document.querySelector("#cartStatus");

const dialog = document.querySelector("#productDialog");
const dialogClose = document.querySelector("#dialogClose");
const dialogImage = document.querySelector("#dialogImage");
const dialogTitle = document.querySelector("#dialogTitle");
const dialogPrice = document.querySelector("#dialogPrice");
const colorGroup = document.querySelector("#colorGroup");
const colorButtons = document.querySelector("#colorButtons");
const sizeGroup = document.querySelector("#sizeGroup");
const sizeButtons = document.querySelector("#sizeButtons");
const addToCartButton = document.querySelector("#addToCart");
const dialogStatus = document.querySelector("#dialogStatus");

let products = [];
let activeProduct = null;
let selectedColor = null;
let selectedSize = null;

async function apiFetch(path, options = {}) {
  const bases = [apiBase, ...apiFallbackBases.filter((b) => b !== apiBase)];
  let lastErr;
  for (const base of bases) {
    try {
      const response = await fetch(`${base}${path}`, options);
      if (response.ok || response.status < 500) return response;
      lastErr = new Error(`HTTP ${response.status} from ${base}`);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("API unreachable");
}

function money(value) {
  return `$${Number.parseFloat(value).toFixed(2)}`;
}

function priceLabel(product) {
  if (product.price_min === product.price_max) return money(product.price_min);
  return `${money(product.price_min)}+`;
}

/* ------------------------------------------------------------- cart -- */

function loadCart() {
  try {
    const raw = window.localStorage.getItem(cartStorageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function saveCart(cart) {
  try {
    window.localStorage.setItem(cartStorageKey, JSON.stringify(cart));
  } catch (_) {}
}

function cartQuantity(cart) {
  return cart.reduce((sum, line) => sum + line.quantity, 0);
}

function cartSubtotal(cart) {
  return cart.reduce((sum, line) => sum + Number.parseFloat(line.price) * line.quantity, 0);
}

function renderCartBadge(cart) {
  const count = cartQuantity(cart);
  cartCountBadge.textContent = String(count);
  cartCountBadge.hidden = count === 0;
}

function changeQuantity(cart, variantId, delta) {
  const line = cart.find((l) => l.sync_variant_id === variantId);
  if (!line) return cart;
  line.quantity += delta;
  const next = cart.filter((l) => l.quantity > 0 && l.quantity <= 10);
  saveCart(next);
  renderCart(next);
  return next;
}

function renderCart(cart) {
  renderCartBadge(cart);
  cartItemsHost.replaceChildren();

  if (!cart.length) {
    const empty = document.createElement("p");
    empty.className = "cart-empty";
    empty.textContent = "Your cart is empty. The tiles are waiting.";
    cartItemsHost.append(empty);
  }

  for (const line of cart) {
    const row = document.createElement("div");
    row.className = "cart-line";

    const img = document.createElement("img");
    img.src = line.image || "logo.png";
    img.alt = "";

    const info = document.createElement("div");
    const name = document.createElement("p");
    name.className = "cart-line-name";
    name.textContent = line.variant_name;
    const price = document.createElement("p");
    price.className = "cart-line-price";
    price.textContent = money(line.price);
    info.append(name, price);

    const qty = document.createElement("div");
    qty.className = "cart-line-qty";
    const minus = document.createElement("button");
    minus.className = "qty-button";
    minus.type = "button";
    minus.textContent = "-";
    minus.setAttribute("aria-label", `Remove one ${line.variant_name}`);
    minus.addEventListener("click", () => changeQuantity(loadCart(), line.sync_variant_id, -1));
    const count = document.createElement("span");
    count.textContent = String(line.quantity);
    const plus = document.createElement("button");
    plus.className = "qty-button";
    plus.type = "button";
    plus.textContent = "+";
    plus.setAttribute("aria-label", `Add one ${line.variant_name}`);
    plus.addEventListener("click", () => changeQuantity(loadCart(), line.sync_variant_id, 1));
    qty.append(minus, count, plus);

    row.append(img, info, qty);
    cartItemsHost.append(row);
  }

  cartSubtotalNode.textContent = money(cartSubtotal(cart));
  checkoutButton.disabled = cart.length === 0;
}

function addLineToCart(variant, productName) {
  const cart = loadCart();
  const existing = cart.find((l) => l.sync_variant_id === variant.id);
  if (existing) {
    existing.quantity = Math.min(10, existing.quantity + 1);
  } else {
    cart.push({
      sync_variant_id: variant.id,
      quantity: 1,
      variant_name: variant.name || productName,
      price: variant.price,
      image: variant.image,
    });
  }
  saveCart(cart);
  renderCart(cart);
}

function openCart() {
  renderCart(loadCart());
  cartOverlay.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeCart() {
  cartOverlay.hidden = true;
  document.body.style.overflow = "";
}

async function startCheckout() {
  const cart = loadCart();
  if (!cart.length) return;
  checkoutButton.disabled = true;
  cartStatus.textContent = "Starting secure checkout...";
  try {
    const response = await apiFetch("/v1/shop/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: cart.map((line) => ({
          sync_variant_id: line.sync_variant_id,
          quantity: line.quantity,
        })),
      }),
    });
    if (!response.ok) {
      const text = await response.text();
      let detail = `Checkout unavailable (${response.status})`;
      try {
        const payload = JSON.parse(text);
        detail = payload.detail || payload.error?.message || detail;
      } catch (_) {}
      throw new Error(typeof detail === "string" ? detail : `Checkout unavailable (${response.status})`);
    }
    const payload = await response.json();
    if (!payload.checkout_url) throw new Error("Checkout did not return a payment URL.");
    window.location.href = payload.checkout_url;
  } catch (err) {
    checkoutButton.disabled = false;
    cartStatus.textContent = err?.message || "Checkout could not start. Please try again.";
    console.error(err);
  }
}

/* ------------------------------------------------------ product dialog -- */

function variantOptions(product) {
  const colors = [];
  const sizes = [];
  for (const v of product.variants) {
    if (v.color && !colors.includes(v.color)) colors.push(v.color);
    if (v.size && !sizes.includes(v.size)) sizes.push(v.size);
  }
  return { colors, sizes };
}

function resolveVariant(product) {
  return product.variants.find((v) => {
    const colorOk = selectedColor === null || v.color === selectedColor;
    const sizeOk = selectedSize === null || v.size === selectedSize;
    return colorOk && sizeOk;
  });
}

function sizeAvailable(product, size) {
  return product.variants.some(
    (v) => v.size === size && (selectedColor === null || v.color === selectedColor),
  );
}

function renderOptionPills(host, values, selected, onPick, disabledCheck) {
  host.replaceChildren();
  for (const value of values) {
    const pill = document.createElement("button");
    pill.className = "option-pill";
    pill.type = "button";
    pill.textContent = value;
    if (value === selected) pill.classList.add("is-selected");
    if (disabledCheck && !disabledCheck(value)) pill.disabled = true;
    pill.addEventListener("click", () => onPick(value));
    host.append(pill);
  }
}

function refreshDialogState() {
  if (!activeProduct) return;
  const { colors, sizes } = variantOptions(activeProduct);

  colorGroup.hidden = colors.length === 0;
  sizeGroup.hidden = sizes.length === 0;

  renderOptionPills(colorButtons, colors, selectedColor, (value) => {
    selectedColor = value;
    if (selectedSize !== null && !sizeAvailable(activeProduct, selectedSize)) selectedSize = null;
    refreshDialogState();
  });
  renderOptionPills(
    sizeButtons,
    sizes,
    selectedSize,
    (value) => {
      selectedSize = value;
      refreshDialogState();
    },
    (value) => sizeAvailable(activeProduct, value),
  );

  const needsColor = colors.length > 0 && selectedColor === null;
  const needsSize = sizes.length > 0 && selectedSize === null;
  const variant = !needsColor && !needsSize ? resolveVariant(activeProduct) : null;

  if (variant) {
    dialogPrice.textContent = money(variant.price);
    if (variant.image) dialogImage.src = variant.image;
    addToCartButton.disabled = false;
    addToCartButton.textContent = "Add to cart";
  } else {
    dialogPrice.textContent = priceLabel(activeProduct);
    addToCartButton.disabled = true;
    addToCartButton.textContent = needsColor && needsSize
      ? "Pick a color and size"
      : needsColor
        ? "Pick a color"
        : needsSize
          ? "Pick a size"
          : "Unavailable";
  }
}

function openProductDialog(product) {
  activeProduct = product;
  const { colors, sizes } = variantOptions(product);
  selectedColor = colors.length === 1 ? colors[0] : null;
  selectedSize = sizes.length === 1 ? sizes[0] : null;
  dialogTitle.textContent = product.name;
  dialogImage.src = product.thumbnail_url || product.variants[0]?.image || "logo.png";
  dialogImage.alt = product.name;
  dialogStatus.textContent = "";
  refreshDialogState();
  dialog.showModal();
}

/* --------------------------------------------------------------- grid -- */

function renderProducts() {
  productGrid.replaceChildren();
  for (const product of products) {
    const card = document.createElement("button");
    card.className = "product-card";
    card.type = "button";

    const media = document.createElement("div");
    media.className = "product-card-media";
    const img = document.createElement("img");
    img.src = product.thumbnail_url || product.variants[0]?.image || "logo.png";
    img.alt = product.name;
    img.loading = "lazy";
    img.decoding = "async";
    media.append(img);

    const info = document.createElement("div");
    info.className = "product-card-info";
    const name = document.createElement("h3");
    name.textContent = product.name;
    const price = document.createElement("span");
    price.className = "product-card-price";
    price.textContent = priceLabel(product);
    info.append(name, price);

    card.append(media, info);
    card.addEventListener("click", () => openProductDialog(product));
    productGrid.append(card);
  }
}

async function loadProducts() {
  try {
    const response = await apiFetch("/v1/shop/products");
    if (!response.ok) throw new Error(`Shop unavailable (${response.status})`);
    const payload = await response.json();
    products = (payload.products || []).filter((p) => p.variants?.length);
    if (!products.length) {
      shopStatus.textContent = "The first drop is being printed. Check back soon.";
      return;
    }
    shopStatus.textContent = "";
    renderProducts();
  } catch (err) {
    shopStatus.textContent = "Could not load the shop right now. Please refresh in a moment.";
    console.error(err);
  }
}

/* --------------------------------------------------------------- init -- */

cartOpenButton.addEventListener("click", openCart);
cartCloseButton.addEventListener("click", closeCart);
cartOverlay.addEventListener("click", (event) => {
  if (event.target === cartOverlay) closeCart();
});
checkoutButton.addEventListener("click", () => void startCheckout());

dialogClose.addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  const rect = dialog.getBoundingClientRect();
  const inside =
    event.clientX >= rect.left &&
    event.clientX <= rect.right &&
    event.clientY >= rect.top &&
    event.clientY <= rect.bottom;
  if (!inside) dialog.close();
});

addToCartButton.addEventListener("click", () => {
  if (!activeProduct) return;
  const variant = resolveVariant(activeProduct);
  if (!variant) return;
  addLineToCart(variant, activeProduct.name);
  dialogStatus.textContent = "Added to cart.";
  window.setTimeout(() => {
    if (dialog.open) dialog.close();
    openCart();
  }, 350);
});

renderCartBadge(loadCart());
void loadProducts();
