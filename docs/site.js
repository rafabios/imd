(() => {
  const versionNodes = document.querySelectorAll("[data-latest-version]");
  if (!versionNodes.length) return;

  fetch("https://api.github.com/repos/rafabios/imd/releases/latest", {
    headers: { Accept: "application/vnd.github+json" },
  })
    .then((response) => {
      if (!response.ok) throw new Error(`GitHub respondeu ${response.status}`);
      return response.json();
    })
    .then((release) => {
      const tag = typeof release.tag_name === "string" ? release.tag_name.trim() : "";
      if (!/^v?\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?$/.test(tag)) return;
      versionNodes.forEach((node) => {
        node.textContent = tag;
      });
    })
    .catch(() => {
      // Mantem a versao de fallback presente no HTML quando a API estiver indisponivel.
    });
})();
