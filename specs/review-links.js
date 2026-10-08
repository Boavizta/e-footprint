(() => {
  const selector = 'a[data-review-source-href][href^="vscode://file/"]';
  const menu = document.createElement("div");
  menu.id = "review-link-menu";
  menu.setAttribute("role", "menu");
  menu.setAttribute("aria-label", "Open source file");
  menu.hidden = true;

  const openFile = document.createElement("a");
  openFile.textContent = "Open file";
  openFile.setAttribute("role", "menuitem");
  const openDiff = document.createElement("a");
  openDiff.textContent = "Open diff vs main";
  openDiff.setAttribute("role", "menuitem");
  menu.append(openFile, openDiff);
  document.body.append(menu);

  let sourceLink = null;

  function closeMenu() {
    menu.hidden = true;
    sourceLink = null;
  }

  function diffUrl(link) {
    const uri = new URL(link.href);
    let filePath = decodeURIComponent(uri.pathname.slice(1));
    const location = filePath.match(/:(\d+)(?::(\d+))?$/);
    if (location) filePath = filePath.slice(0, -location[0].length);

    const query = new URLSearchParams({ path: filePath });
    if (location) {
      query.set("line", location[1]);
      if (location[2]) query.set("column", location[2]);
    }
    return `vscode://local.plan-review-links/diff?${query}`;
  }

  document.addEventListener("contextmenu", (event) => {
    const link = event.target.closest(selector);
    if (!link) {
      closeMenu();
      return;
    }

    event.preventDefault();
    sourceLink = link;
    openFile.href = link.href;
    openDiff.href = diffUrl(link);
    menu.hidden = false;

    const bounds = link.getBoundingClientRect();
    const x = event.clientX || bounds.left;
    const y = event.clientY || bounds.bottom;
    menu.style.left = `${Math.max(8, Math.min(x, window.innerWidth - menu.offsetWidth - 8))}px`;
    menu.style.top = `${Math.max(8, Math.min(y, window.innerHeight - menu.offsetHeight - 8))}px`;
    openDiff.focus();
  });

  document.addEventListener("pointerdown", (event) => {
    if (!menu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (menu.hidden) return;
    if (event.key === "Escape") {
      const link = sourceLink;
      closeMenu();
      link?.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      (document.activeElement === openDiff ? openFile : openDiff).focus();
    }
  });
  window.addEventListener("scroll", closeMenu, true);
  window.addEventListener("resize", closeMenu);
  menu.addEventListener("click", closeMenu);
})();
