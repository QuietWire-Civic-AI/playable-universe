const grid = document.querySelector("#tile-grid");
const filters = [...document.querySelectorAll(".filter")];
let tiles = [];

function esc(value = "") {
  return String(value).replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[ch]);
}

function badge(label, cls = "") {
  return '<span class="badge ' + cls + '">' + esc(label) + "</span>";
}

function render(layer = "all") {
  const shown = layer === "all" ? tiles : tiles.filter(t => t.layer === layer);
  if (!shown.length) {
    grid.innerHTML = '<p class="loading">No tiles in this layer yet.</p>';
    return;
  }
  grid.innerHTML = shown.map(t => {
    const valleyClass = t.design_valley === "inside" ? "inside" :
      t.design_valley === "outside" ? "outside" : "";
    const assumptions = (t.assumptions || []).length
      ? '<ul class="assumptions">' + t.assumptions.map(a => "<li>" + esc(a) + "</li>").join("") + "</ul>"
      : "";
    return '<article class="tile" data-layer="' + esc(t.layer) + '">' +
      '<div class="tile-head"><div class="badges">' +
      badge(t.layer) + badge(t.status) +
      (t.design_valley && t.design_valley !== "not_applicable" ? badge("design valley: " + t.design_valley, valleyClass) : "") +
      '</div></div>' +
      '<h3>' + esc(t.title) + '</h3>' +
      '<p class="meta">' + esc(t.date_label || "") + (t.place ? " · " + esc(t.place) : "") + '</p>' +
      '<p class="summary">' + esc(t.summary) + '</p>' +
      assumptions +
      '<div class="source-ref">source: ' + esc(t.source_ref || "working rendering") + '</div>' +
      '</article>';
  }).join("");
}

filters.forEach(button => {
  button.addEventListener("click", () => {
    filters.forEach(b => b.classList.remove("active"));
    button.classList.add("active");
    render(button.dataset.layer);
  });
});

fetch("./data/tiles.json", {cache: "no-store"})
  .then(r => {
    if (!r.ok) throw new Error("tiles " + r.status);
    return r.json();
  })
  .then(data => {
    tiles = data;
    render("all");
  })
  .catch(err => {
    console.error(err);
    grid.innerHTML = '<p class="loading">The tile index could not be loaded. The static world frame is still available.</p>';
  });
