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
</body>
</html>
`;

writeFileSync(join(siteDir, "index.html"), html, "utf8");
console.log(`prerendered ${join(siteDir, "index.html")}`);
