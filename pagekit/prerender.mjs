import { build } from "esbuild";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteDir = process.argv[2];
if (!siteDir) {
  console.error("usage: node prerender.mjs <site-dir>");
  process.exit(1);
}

const workDir = mkdtempSync(join(tmpdir(), "pagekit-"));
const entry = join(workDir, "entry.jsx");
const outfile = join(workDir, "render.cjs");

writeFileSync(
  entry,
  `import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import App from ${JSON.stringify(join(siteDir, "App.jsx"))};

export function renderPage() {
  return renderToStaticMarkup(React.createElement(App));
}
`,
  "utf8",
);

await build({
  absWorkingDir: here,
  entryPoints: [entry],
  bundle: true,
  platform: "node",
  format: "cjs",
  outfile,
  jsx: "transform",
  jsxFactory: "React.createElement",
  jsxFragment: "React.Fragment",
  nodePaths: [join(here, "node_modules")],
});

const { renderPage } = createRequire(import.meta.url)(outfile);
const body = renderPage();
const css = readFileSync(join(siteDir, "tokens.css"), "utf8");
const page = JSON.parse(readFileSync(join(siteDir, "page.json"), "utf8"));
const title = page.title || "Sales page";
const lang = page.language || page.lang || "en";
const dir = page.dir || (lang === "he" ? "rtl" : "ltr");
const dirAttr = dir === "rtl" ? ' dir="rtl"' : "";

const html = `<!DOCTYPE html>
<html lang="${lang}"${dirAttr}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
  <style>${css}</style>
</head>
<body>
${body}
<script>
(function () {
  var root = document.querySelector("[data-offer-ends]");
  if (!root) return;
  var end = Date.parse(root.getAttribute("data-offer-ends"));
  if (!end) return;
  function pad(n) { return String(n).padStart(2, "0"); }
  function tick() {
    var left = end - Date.now();
    var face = root.querySelector(".countdown-face");
    var expired = root.querySelector(".countdown-expired");
    if (left <= 0) {
      if (face) face.setAttribute("hidden", "");
      if (expired) expired.removeAttribute("hidden");
      return;
    }
    if (face) face.removeAttribute("hidden");
    if (expired) expired.setAttribute("hidden", "");
    var total = Math.floor(left / 1000);
    var map = {
      h: Math.floor(total / 3600),
      m: Math.floor((total % 3600) / 60),
      s: total % 60
    };
    Object.keys(map).forEach(function (unit) {
      var el = root.querySelector('[data-unit="' + unit + '"]');
      if (el) el.textContent = pad(map[unit]);
    });
    setTimeout(tick, 250);
  }
  tick();
})();
(function () {
  var modal = document.getElementById("lead");
  if (!modal) return;
  var form = modal.querySelector("[data-lead-form]");
  var formWrap = modal.querySelector("[data-lead-form-wrap]");
  var thanks = modal.querySelector("[data-lead-thanks]");
  var errorEl = modal.querySelector("[data-lead-error]");
  function openModal(event) {
    if (event) event.preventDefault();
    modal.removeAttribute("hidden");
  }
  function closeModal() {
    modal.setAttribute("hidden", "");
  }
  document.querySelectorAll("[data-open-lead]").forEach(function (el) {
    el.addEventListener("click", openModal);
  });
  modal.querySelectorAll("[data-lead-close]").forEach(function (el) {
    el.addEventListener("click", closeModal);
  });
  if (!form) return;
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var slug = form.getAttribute("data-lead-slug") || "";
    var payload = {
      name: (form.elements.name && form.elements.name.value) || "",
      email: (form.elements.email && form.elements.email.value) || "",
      phone: (form.elements.phone && form.elements.phone.value) || ""
    };
    if (errorEl) errorEl.setAttribute("hidden", "");
    fetch("/api/pages/" + encodeURIComponent(slug) + "/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          if (errorEl) errorEl.removeAttribute("hidden");
          return;
        }
        var next = result.data && result.data.next_url;
        if (next && /^https?:\\/\\//i.test(next)) {
          window.location.assign(next);
          return;
        }
        if (formWrap) formWrap.setAttribute("hidden", "");
        if (thanks) thanks.removeAttribute("hidden");
      })
      .catch(function () {
        if (errorEl) errorEl.removeAttribute("hidden");
      });
  });
})();
</script>
</body>
</html>
`;

writeFileSync(join(siteDir, "index.html"), html, "utf8");
console.log(`prerendered ${join(siteDir, "index.html")}`);
