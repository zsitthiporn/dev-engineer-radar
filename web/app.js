"use strict";
(() => {
  const search = document.querySelector("#search");
  if (!search) return;
  const cards = [...document.querySelectorAll(".story-card")];
  const filters = [...document.querySelectorAll("[data-filter]")];
  const verdict = document.querySelector("#verdict");
  const params = new URLSearchParams(location.search);
  let topic = filters.some(b => b.dataset.filter === params.get("topic")) ? params.get("topic") : "all";
  search.value = params.get("q") || "";
  if ([...verdict.options].some(o => o.value === params.get("verdict"))) verdict.value = params.get("verdict");
  function update() {
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/u).filter(Boolean);
    let count = 0;
    for (const card of cards) {
      const visible = (topic === "all" || card.dataset.topic === topic)
        && (verdict.value === "all" || card.dataset.recommendation === verdict.value)
        && terms.every(term => card.dataset.search.includes(term));
      card.hidden = !visible;
      if (visible) count++;
    }
    filters.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.filter === topic)));
    document.querySelector("#result-count").textContent = `${count} บทความ · คัดจาก primary sources`;
    document.querySelector("#empty").hidden = count > 0;
    const query = new URLSearchParams();
    if (search.value.trim()) query.set("q", search.value.trim());
    if (topic !== "all") query.set("topic", topic);
    if (verdict.value !== "all") query.set("verdict", verdict.value);
    history.replaceState(null, "", `${location.pathname}${query.size ? "?" + query : ""}${location.hash}`);
  }
  filters.forEach(b => b.addEventListener("click", () => { topic = b.dataset.filter; update(); }));
  search.addEventListener("input", update);
  verdict.addEventListener("change", update);
  document.querySelector("#reset").addEventListener("click", () => { search.value = ""; topic = "all"; verdict.value = "all"; update(); search.focus(); });
  document.addEventListener("keydown", e => {
    if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !document.activeElement.isContentEditable) { e.preventDefault(); search.focus(); }
  });
  update();
})();
