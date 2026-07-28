(() => {
  "use strict";

  const GITHUB_REPOSITORY = "https://github.com/Boavizta/e-footprint";
  const DEFAULT_BRANCH = "main";
  const STORAGE_KEY = "e-footprint-architecture-source-branch";
  const VALID_BRANCH = /^[A-Za-z0-9._/-]+$/;

  const query = new URLSearchParams(window.location.search);
  const requestedBranch = query.get("branch");
  const embedded = query.has("embed");
  if (embedded) document.documentElement.classList.add("embed");

  function readStoredBranch() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (_error) {
      return null;
    }
  }

  function storeBranch(branch) {
    try {
      window.localStorage.setItem(STORAGE_KEY, branch);
    } catch (_error) {
      // Query-string propagation still keeps the setting across architecture pages.
    }
  }

  const storedBranch = readStoredBranch();
  const branch = requestedBranch && VALID_BRANCH.test(requestedBranch)
    ? requestedBranch
    : storedBranch && VALID_BRANCH.test(storedBranch)
      ? storedBranch
      : DEFAULT_BRANCH;
  storeBranch(branch);

  const helperUrl = new URL(document.currentScript.src, document.baseURI);
  const architectureRoot = new URL("./", helperUrl);
  const repositoryRoot = new URL("../../", architectureRoot);

  function githubBranchPath(value) {
    return value.split("/").map(encodeURIComponent).join("/");
  }

  function rewriteLinks() {
    document.querySelectorAll("a[href]").forEach((anchor) => {
      const originalHref = anchor.dataset.originalHref || anchor.getAttribute("href");
      anchor.dataset.originalHref = originalHref;
      if (!originalHref || originalHref.startsWith("#")) return;

      let target;
      try {
        target = new URL(originalHref, document.baseURI);
      } catch (_error) {
        return;
      }

      if (target.pathname.startsWith(architectureRoot.pathname)
          && target.pathname.endsWith(".html")) {
        target.searchParams.set("branch", branch);
        anchor.href = target.href;
        return;
      }

      if (target.pathname.startsWith(repositoryRoot.pathname)
          && !target.pathname.startsWith(architectureRoot.pathname)) {
        const repositoryPath = target.pathname.slice(repositoryRoot.pathname.length);
        anchor.href = `${GITHUB_REPOSITORY}/blob/${githubBranchPath(branch)}/${repositoryPath}${target.hash}`;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.title = `Open ${repositoryPath} on GitHub (${branch})`;
      }
    });
  }

  function installBranchPicker() {
    const style = document.createElement("style");
    style.textContent = `
      .source-branch-picker { display:flex; align-items:center; flex-wrap:wrap; gap:.45rem;
        margin:0 0 1rem; padding:.48rem .65rem; border:1px solid #dbe3ee; border-radius:10px;
        background:#fff; color:#64748b; font: .78rem system-ui,-apple-system,sans-serif; }
      .source-branch-picker label { font-weight:650; color:#172033; }
      .source-branch-picker input { width:9rem; border:1px solid #cbd5e1; border-radius:6px;
        padding:.25rem .4rem; font:inherit; color:#172033; background:#f8fafc; }
      .source-branch-picker button { border:0; border-radius:6px; padding:.3rem .55rem;
        background:#047857; color:#fff; font:inherit; font-weight:650; cursor:pointer; }
      .source-branch-picker .source-branch-note { margin-left:auto; }
      #architecture-dock { position:fixed; z-index:20; top:0; right:0; bottom:0;
        width:min(74rem,62vw); display:flex; flex-direction:column; background:#fff;
        border-left:1px solid #dbe3ee; box-shadow:-8px 0 28px rgba(15,23,42,.14); }
      #architecture-dock[hidden] { display:none; }
      .architecture-dockbar { display:flex; justify-content:space-between; align-items:center; gap:.6rem;
        padding:.65rem .9rem; border-bottom:1px solid #dbe3ee; background:#f8fafc;
        font:.82rem system-ui,-apple-system,sans-serif; }
      .architecture-dockbar .title { font-weight:700; color:#172033; }
      .architecture-dockbar .actions { display:flex; align-items:center; gap:.8rem; white-space:nowrap; }
      .architecture-dockbar a { color:#047857; text-decoration:none; }
      .architecture-dockbar button { border:0; background:none; color:#64748b; cursor:pointer; font-size:1rem; }
      #architecture-dock-frame { flex:1; width:100%; border:0; }
      body.architecture-docked { max-width:none !important;
        margin-left:2.5rem !important; margin-right:calc(min(74rem,62vw) + 2rem) !important; }
      a.term { color:#6d28d9; text-decoration-line:underline; text-decoration-style:dotted;
        text-underline-offset:.18em; cursor:help; }
      #architecture-glossary { position:fixed; z-index:30; left:0; right:0; bottom:0;
        height:min(18rem,38vh); display:flex; flex-direction:column; background:#fff;
        border-top:2px solid #7c3aed; box-shadow:0 -10px 30px rgba(15,23,42,.18); }
      #architecture-glossary[hidden] { display:none; }
      .architecture-glossarybar { display:flex; justify-content:space-between; align-items:center; gap:.6rem;
        padding:.52rem .9rem; border-bottom:1px solid #dbe3ee; background:#f5f3ff;
        font:.82rem system-ui,-apple-system,sans-serif; }
      .architecture-glossarybar .title { font-weight:700; color:#5b21b6; }
      .architecture-glossarybar .actions { display:flex; align-items:center; gap:.8rem; white-space:nowrap; }
      .architecture-glossarybar a { color:#6d28d9; text-decoration:none; }
      .architecture-glossarybar button { border:0; background:none; color:#64748b; cursor:pointer; font-size:1rem; }
      #architecture-glossary-frame { flex:1; width:100%; border:0; }
      @media(max-width:36rem) { .source-branch-picker .source-branch-note { width:100%; margin-left:0; } }
    `;
    document.head.appendChild(style);

    // Embedded technical zooms still need the dotted term affordance, but not
    // their own branch controls—the parent architecture page owns those.
    if (embedded) return;

    const form = document.createElement("form");
    form.className = "source-branch-picker";
    form.innerHTML = `
      <label for="source-branch">GitHub source branch</label>
      <input id="source-branch" name="branch" value="${branch}"
             pattern="[A-Za-z0-9._/-]+" aria-label="GitHub source branch">
      <button type="submit">Use branch</button>
      <span class="source-branch-note">Repository links open on GitHub · default <code>main</code></span>
    `;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = form.elements.branch;
      const nextBranch = input.value.trim();
      if (!VALID_BRANCH.test(nextBranch)) {
        input.setCustomValidity("Use letters, numbers, dot, underscore, slash, or hyphen.");
        input.reportValidity();
        return;
      }
      input.setCustomValidity("");
      storeBranch(nextBranch);
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set("branch", nextBranch);
      window.location.assign(nextUrl.href);
    });
    document.body.insertBefore(form, document.body.firstChild);
  }

  function installDock() {
    const zoomLinks = Array.from(document.querySelectorAll("a.zoom"));
    if (!zoomLinks.length || embedded) return;

    const dock = document.createElement("aside");
    dock.id = "architecture-dock";
    dock.hidden = true;
    dock.innerHTML = `
      <div class="architecture-dockbar">
        <span class="title" id="architecture-dock-title">technical zoom</span>
        <span class="actions">
          <a id="architecture-dock-open" href="#" target="_blank" rel="noopener noreferrer">open full page ↗</a>
          <button id="architecture-dock-close" type="button" title="Close technical zoom" aria-label="Close">✕</button>
        </span>
      </div>
      <iframe id="architecture-dock-frame" title="Technical zoom"></iframe>
    `;
    document.body.appendChild(dock);
    const frame = dock.querySelector("#architecture-dock-frame");
    const title = dock.querySelector("#architecture-dock-title");
    const open = dock.querySelector("#architecture-dock-open");

    function closeDock() {
      dock.hidden = true;
      frame.src = "about:blank";
      document.body.classList.remove("architecture-docked");
    }

    dock.querySelector("#architecture-dock-close").addEventListener("click", closeDock);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !document.body.classList.contains("architecture-glossary-open")) closeDock();
    });
    zoomLinks.forEach((anchor) => {
      anchor.addEventListener("click", (event) => {
        if (window.innerWidth < 1100 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        const frameUrl = new URL(anchor.href);
        frameUrl.searchParams.set("embed", "1");
        frame.src = frameUrl.href;
        open.href = anchor.href;
        title.textContent = (anchor.dataset.title || anchor.textContent.replace("🔍", "")).trim();
        dock.hidden = false;
        document.body.classList.add("architecture-docked");
      });
    });
  }

  function installGlossaryDrawer() {
    const termLinks = Array.from(document.querySelectorAll("a.term"));
    if (!termLinks.length && embedded) return;

    if (embedded) {
      termLinks.forEach((anchor) => {
        anchor.addEventListener("click", (event) => {
          if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || window.parent === window) return;
          event.preventDefault();
          window.parent.postMessage({
            type: "e-footprint:open-glossary",
            href: anchor.href,
            title: (anchor.dataset.title || anchor.textContent).trim()
          }, "*");
        });
      });
      return;
    }

    const drawer = document.createElement("aside");
    drawer.id = "architecture-glossary";
    drawer.hidden = true;
    drawer.setAttribute("aria-label", "Glossary definition");
    drawer.innerHTML = `
      <div class="architecture-glossarybar">
        <span class="title" id="architecture-glossary-title">term</span>
        <span class="actions">
          <a id="architecture-glossary-open" href="glossary.html" target="_blank" rel="noopener noreferrer">open full glossary ↗</a>
          <button id="architecture-glossary-close" type="button" title="Close definition" aria-label="Close definition">✕</button>
        </span>
      </div>
      <iframe id="architecture-glossary-frame" title="Glossary definition"></iframe>
    `;
    document.body.appendChild(drawer);
    const frame = drawer.querySelector("#architecture-glossary-frame");
    const title = drawer.querySelector("#architecture-glossary-title");
    const open = drawer.querySelector("#architecture-glossary-open");

    function closeDrawer() {
      drawer.hidden = true;
      frame.src = "about:blank";
      document.body.classList.remove("architecture-glossary-open");
    }

    function openDefinition(href, label) {
      let definitionUrl;
      try {
        definitionUrl = new URL(href, document.baseURI);
      } catch (_error) {
        return;
      }
      if (!definitionUrl.pathname.startsWith(architectureRoot.pathname)
          || !definitionUrl.pathname.endsWith("glossary.html")) return;
      const fullUrl = new URL(definitionUrl.href);
      definitionUrl.searchParams.set("embed", "glossary");
      definitionUrl.searchParams.set("branch", branch);
      frame.src = definitionUrl.href;
      open.href = fullUrl.href;
      title.textContent = label || "Glossary definition";
      drawer.hidden = false;
      document.body.classList.add("architecture-glossary-open");
    }

    drawer.querySelector("#architecture-glossary-close").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !drawer.hidden) {
        event.stopImmediatePropagation();
        closeDrawer();
      }
    }, true);
    termLinks.forEach((anchor) => {
      anchor.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        openDefinition(anchor.href, (anchor.dataset.title || anchor.textContent).trim());
      });
    });
    window.addEventListener("message", (event) => {
      if (!event.data || event.data.type !== "e-footprint:open-glossary") return;
      openDefinition(event.data.href, event.data.title);
    });
  }

  rewriteLinks();
  installBranchPicker();
  installDock();
  installGlossaryDrawer();
})();
