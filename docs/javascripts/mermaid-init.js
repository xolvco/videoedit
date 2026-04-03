function renderMermaidDiagrams() {
  if (typeof mermaid === "undefined") {
    return;
  }

  mermaid.initialize({ startOnLoad: false });

  const diagrams = document.querySelectorAll(".mermaid");
  for (const diagram of diagrams) {
    if (diagram.dataset.processed === "true") {
      continue;
    }
    diagram.removeAttribute("data-processed");
  }

  mermaid.run({ querySelector: ".mermaid" });
}

document.addEventListener("DOMContentLoaded", renderMermaidDiagrams);

if (typeof window.document$ !== "undefined") {
  window.document$.subscribe(function () {
    renderMermaidDiagrams();
  });
}
