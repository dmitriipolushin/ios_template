// Shoots an HTML prototype state by state, at the device's size, for a pixel comparison with
// the app's screenshots.
//
//   node shoot.mjs <prototype.html> <states.json> <outDir>
//        [--width 402] [--height 874] [--scale 3]
//        [--screen ".screen.on"] [--scroll ".screen.on .scroll"]
//        [--geometry ".greet,.card,.rowline,.pill,.eyebrow,.note"] [--only name1,name2]
//
// states.json: [{ "name": "35_support", "js": ["nav('you')", "openSupport()"],
//                 "wait": 700, "scroll": true, "geometry": [".card"], "text": true }]
//   js        code run in the page after load, one string or a list of steps
//   wait      ms after the steps (default 700); stepWait between steps (default 350)
//   scroll    also shoot the scrolled screen page by page: <name>_p1.png, _p2.png ...
//   geometry  selectors whose boxes and type go to <name>.geo.json (adds to --geometry)
//   root      where to look for them; default: the topmost open overlay matching --root
//             ('[id$="Scr"].on, .sheet.on, [role="dialog"]'), else the active screen
//   text      the visible text of the active screen and open overlays to <name>.txt
//
// Per state it writes <name>.png (width*scale x height*scale), <name>.txt, <name>.geo.json.
// Coordinates in .geo.json are CSS px = points at the device size, y from the top of the page
// (the prototype has no status bar: 0 is where the device's safe area would start or not;
// see references/method.md for the per-screen offset).
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { chromiumPath, flags } from './chromium.mjs';

const [,, protoPath, statesPath, outDir, ...rest] = process.argv;
if (!protoPath || !statesPath || !outDir) {
  console.error('usage: node shoot.mjs <prototype.html> <states.json> <outDir> [--width 402 --height 874 --scale 3]');
  process.exit(2);
}
const opt = flags(rest);
const width = Number(opt.width ?? 402), height = Number(opt.height ?? 874), scale = Number(opt.scale ?? 3);
const screenSel = opt.screen ?? '.screen.on';
const scrollSel = opt.scroll ?? '.screen.on .scroll';
const baseGeometry = String(opt.geometry ?? '.greet,h1,h2,.card,.rowline,.pill,.eyebrow,.note,button').split(',').filter(Boolean);
const only = opt.only ? new Set(String(opt.only).split(',')) : null;
const rootDefault = opt.root ?? '[id$="Scr"].on, .sheet.on, [role="dialog"], [role="alertdialog"]';

let states = JSON.parse(fs.readFileSync(statesPath, 'utf8'));
if (only) states = states.filter(s => only.has(s.name));
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ executablePath: chromiumPath(), headless: true });
const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: scale, isMobile: true, hasTouch: true });
const url = 'file://' + path.resolve(protoPath);

for (const s of states) {
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log(`[${s.name}] pageerror: ${e.message}`));
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  for (const step of [].concat(s.js ?? [])) {
    if (!step) continue;
    try { await page.evaluate(step); } catch (e) { console.log(`[${s.name}] js error: ${e.message}`); }
    await page.waitForTimeout(s.stepWait ?? 350);
  }
  await page.waitForTimeout(s.wait ?? 700);
  await page.screenshot({ path: path.join(outDir, s.name + '.png') });

  if (s.text !== false) {
    const txt = await page.evaluate((screenSel) => {
      const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; };
      const parts = [];
      const seen = new Set();
      document.querySelectorAll(screenSel + ', [role="dialog"], [role="alertdialog"], .sheet.on, .on[id$="Sheet"]').forEach(el => {
        if (!vis(el) || seen.has(el)) return; seen.add(el);
        parts.push('### ' + (el.id || el.className) + '\n' + el.innerText);
      });
      return parts.join('\n\n');
    }, screenSel);
    fs.writeFileSync(path.join(outDir, s.name + '.txt'), txt);
  }

  const selectors = baseGeometry.concat(s.geometry ?? []);
  const geo = await page.evaluate(({ screenSel, selectors, rootSel }) => {
    // The topmost open overlay (a full-screen page, a sheet, a dialog) is what the state shows;
    // the screen under it otherwise.
    const isVis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; };
    const overlays = [...document.querySelectorAll(rootSel)].filter(isVis);
    const root = overlays.length ? overlays[overlays.length - 1] : (document.querySelector(screenSel) || document.body);
    const out = [];
    const seen = new Set();
    for (const sel of selectors) {
      for (const el of root.querySelectorAll(sel)) {
        if (seen.has(el)) continue;
        const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
        if (r.width === 0 || r.height === 0 || cs.display === 'none' || cs.visibility === 'hidden') continue;
        seen.add(el);
        const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
        out.push({ sel, tag: el.tagName.toLowerCase(), id: el.id || undefined,
          cls: typeof el.className === 'string' ? el.className : undefined,
          text: (own || el.innerText || '').trim().slice(0, 80) || undefined,
          x: +r.x.toFixed(2), y: +r.y.toFixed(2), w: +r.width.toFixed(2), h: +r.height.toFixed(2),
          font: `${cs.fontSize} ${cs.fontWeight}`, lineHeight: cs.lineHeight, letterSpacing: cs.letterSpacing,
          color: cs.color, bg: cs.backgroundColor !== 'rgba(0, 0, 0, 0)' ? cs.backgroundColor : undefined,
          radius: cs.borderRadius !== '0px' ? cs.borderRadius : undefined,
          margin: cs.margin !== '0px' ? cs.margin : undefined, padding: cs.padding !== '0px' ? cs.padding : undefined });
      }
    }
    return out.sort((a, b) => a.y - b.y || a.x - b.x);
  }, { screenSel, selectors, rootSel: s.root ?? rootDefault });
  fs.writeFileSync(path.join(outDir, s.name + '.geo.json'), JSON.stringify(geo, null, 1));

  if (s.scroll) {
    const info = await page.evaluate((scrollSel) => {
      const scr = document.querySelector(scrollSel);
      return scr ? { h: scr.scrollHeight, c: scr.clientHeight } : null;
    }, scrollSel);
    if (info && info.h > info.c + 4) {
      let pos = 0, i = 1;
      while (pos + info.c < info.h && i < 12) {
        pos = Math.min(pos + Math.round(info.c * 0.8), info.h - info.c);
        await page.evaluate(({ scrollSel, pos }) => { document.querySelector(scrollSel).scrollTop = pos; }, { scrollSel, pos });
        await page.waitForTimeout(250);
        await page.screenshot({ path: path.join(outDir, `${s.name}_p${i}.png`) });
        i++;
      }
    }
  }
  console.log('shot', s.name);
  await page.close();
}
await browser.close();
