// Screenshot every page at phone and desktop width, check for horizontal overflow,
// and tap glossary terms. Usage: node scripts/check.cjs <baseUrl> <outDir>
// Needs Playwright (resolved from NODE_PATH or a global install); does not install browsers.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const base = process.argv[2] || "http://localhost:4173";
const outDir = process.argv[3] || path.join(__dirname, "..", "screenshots");
const pages = ["/", "/mechanism/", "/pipeline/", "/results/", "/prior-art/", "/agent-demo/", "/glossary/"];
const sizes = [
  { name: "375", width: 375, height: 812 },
  { name: "1280", width: 1280, height: 800 },
];

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  let failures = 0;
  for (const scheme of ["light", "dark"]) {
    for (const s of sizes) {
      const ctx = await browser.newContext({ viewport: { width: s.width, height: s.height }, colorScheme: scheme, deviceScaleFactor: 1 });
      const page = await ctx.newPage();
      const errors = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      page.on("request", (r) => {
        if (!r.url().startsWith(base) && !r.url().startsWith("data:")) errors.push("external request: " + r.url());
      });
      for (const p of pages) {
        await page.goto(base + p, { waitUntil: "networkidle" });
        const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
        const ok = o.sw <= o.cw;
        if (!ok) failures++;
        const nm = (p === "/" ? "overview" : p.replace(/\//g, "")) + `-${s.name}` + (scheme === "dark" ? "-dark" : "");
        if (scheme === "light" || p === "/" || p === "/results/") {
          await page.screenshot({ path: path.join(outDir, nm + ".png"), fullPage: false });
        }
        console.log(`${ok ? "OK " : "OVERFLOW"} ${scheme} ${s.name} ${p} scrollWidth=${o.sw} clientWidth=${o.cw}`);
      }
      // Glossary taps (only meaningful if terms exist)
      if (scheme === "light") {
        for (const p of ["/", "/mechanism/", "/results/"]) {
          await page.goto(base + p, { waitUntil: "networkidle" });
          const terms = page.locator("main button.term[data-term]");
          const n = await terms.count();
          if (!n) {
            console.log(`TERMS none on ${p} (${s.name})`);
            continue;
          }
          const t = terms.nth(Math.min(2, n - 1));
          const id = await t.getAttribute("data-term");
          await t.scrollIntoViewIfNeeded();
          await t.click();
          const sheet = page.locator("[data-glossary-sheet]");
          await sheet.waitFor({ state: "visible", timeout: 3000 });
          const title = await sheet.locator("h2").innerText();
          const nested = sheet.locator("button[data-term]");
          let nestedInfo = "";
          if ((await nested.count()) > 0) {
            await nested.first().click();
            nestedInfo = " -> nested " + (await sheet.locator("h2").innerText());
            const back = sheet.getByRole("button", { name: /back/i });
            nestedInfo += (await back.count()) ? " (back button present)" : " (NO back button)";
          }
          if (p === "/mechanism/") await page.screenshot({ path: path.join(outDir, `glossary-sheet-${s.name}.png`) });
          await page.keyboard.press("Escape");
          await sheet.waitFor({ state: "detached", timeout: 3000 });
          // keyboard open
          await t.focus();
          await page.keyboard.press("Enter");
          await sheet.waitFor({ state: "visible", timeout: 3000 });
          const focusInside = await page.evaluate(() => !!document.activeElement?.closest("[data-glossary-sheet]"));
          for (let i = 0; i < 12; i++) await page.keyboard.press("Tab");
          const stillInside = await page.evaluate(() => !!document.activeElement?.closest("[data-glossary-sheet]"));
          await page.keyboard.press("Escape");
          console.log(`TERM ${s.name} ${p}: tapped "${id}" -> sheet "${title}"${nestedInfo}; focus in sheet=${focusInside}, trapped after 12 tabs=${stillInside}`);
          if (title.trim() !== id || !focusInside || !stillInside) failures++;
        }
        // mobile menu
        if (s.width < 768) {
          await page.goto(base + "/", { waitUntil: "networkidle" });
          await page.getByRole("button", { name: /menu/i }).click();
          await page.screenshot({ path: path.join(outDir, "nav-menu-375.png") });
          await page.getByRole("link", { name: "Results" }).click();
          await page.waitForURL(/results/);
          console.log("NAV mobile menu -> " + page.url());
        }
      }
      if (errors.length) {
        failures += errors.length;
        console.log("ERRORS", errors);
      }
      await ctx.close();
    }
  }
  await browser.close();
  console.log(failures ? `FAILURES: ${failures}` : "ALL CHECKS PASSED");
  process.exit(failures ? 1 : 0);
})();
