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
const zoomRange = document.querySelector("#zoomRange");
const contrastRange = document.querySelector("#contrastRange");
const demoImage = document.querySelector("#demoImage");
const demoStats = document.querySelector("#demoStats");
const previewFrame = document.querySelector(".preview-frame");

function renderStats(example) {
  demoStats.innerHTML = `
    <strong>${example.shape}</strong>
    <span>${example.units}</span>
    <span>${example.pixels}</span>
    <span>${example.tiles}</span>
    <span>${example.formats}</span>
  `;
}

function updateDemo() {
  const example = examples[shapeSelect.value];
  demoImage.src = example.src;
  demoImage.alt = example.alt;
  renderStats(example);
}

function updateDisplay() {
  previewFrame.style.setProperty("--zoom", String(Number(zoomRange.value) / 100));
  previewFrame.style.setProperty("--contrast", String(Number(contrastRange.value) / 100));
}

shapeSelect.addEventListener("change", updateDemo);
zoomRange.addEventListener("input", updateDisplay);
contrastRange.addEventListener("input", updateDisplay);

updateDemo();
updateDisplay();
