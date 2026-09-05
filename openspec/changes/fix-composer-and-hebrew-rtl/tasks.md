## 1. Studio composer

- [x] 1.1 Make the thread pane fill remaining height (`.thread { flex: 1; min-height: 0; }`) so the composer stays at the bottom and verify with few messages the input is at the bottom of the center pane
- [x] 1.2 Verify a long thread scrolls above the composer while the composer stays visible at the bottom (including the stacked mobile layout)
- [x] 1.3 On send, append the user message to the thread and clear the composer immediately; verify the box is empty and the bubble is visible while generate is still running

## 2. Hebrew RTL sales pages

- [x] 2.1 Persist page `language` / `dir` from copy or Hebrew-script detection onto `page.json` and verify a Hebrew brief yields `he` + `rtl`
- [x] 2.2 Change `pagekit/prerender.mjs` to emit `<html lang="…" dir="…">` from that data (not hardcoded `en`) and verify Hebrew `index.html` has `lang="he"` and `dir="rtl"`
- [x] 2.3 Add RTL styles (logical alignment / `[dir="rtl"]`) so Hebrew headlines and body align to the start edge and verify an English page remains LTR without `dir="rtl"`
- [x] 2.4 Confirm the studio chrome stays LTR while the preview iframe shows the RTL Hebrew page
