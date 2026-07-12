(() => {
  const indexUrl = "search-index.json";

  async function loadIndex() {
    const res = await fetch(indexUrl);
    if (!res.ok) return [];
    return res.json();
  }

  function pickRandom(items) {
    if (!items.length) return null;
    const pool = items.filter((item) => item.slug !== "index");
    return pool[Math.floor(Math.random() * pool.length)];
  }

  document.querySelector("[data-wiki-random]")?.addEventListener("click", async () => {
    const items = await loadIndex();
    const choice = pickRandom(items);
    if (choice) window.location.href = `${choice.slug}.html`;
  });

  const params = new URLSearchParams(window.location.search);
  const query = (params.get("q") || "").trim().toLowerCase();
  if (!query) return;

  loadIndex().then((items) => {
    const matches = items
      .map((item) => {
        const hay = `${item.title} ${item.summary} ${(item.categories || []).join(" ")}`.toLowerCase();
        const score = hay.includes(query) ? (item.title.toLowerCase().startsWith(query) ? 3 : 1) : 0;
        return { item, score };
      })
      .filter((row) => row.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((row) => row.item);

    const host = document.querySelector(".wiki-content");
    if (!host) return;

    const box = document.createElement("section");
    box.className = "wiki-search-results";
    box.innerHTML = `<h2 id="search-results">Search results for “${query.replace(/"/g, "&quot;")}”</h2>`;
    const list = document.createElement("ul");
    list.className = "wiki-feature-list";

    if (!matches.length) {
      list.innerHTML = "<li>No articles matched. Try a shorter keyword.</li>";
    } else {
      matches.forEach((item) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = `${item.slug}.html`;
        a.textContent = item.title;
        li.appendChild(a);
        const p = document.createElement("p");
        p.textContent = item.summary;
        li.appendChild(p);
        list.appendChild(li);
      });
    }

    box.appendChild(list);
    host.prepend(box);
    document.querySelector(".wiki-title")?.focus?.();
  });
})();
