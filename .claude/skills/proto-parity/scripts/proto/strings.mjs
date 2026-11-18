// Every piece of text the prototype can show, screen by screen, for the copy check: the text of
// each screen, sheet and dialog container as rendered after load (hidden ones included, since a
// state may reveal them). Strings that only exist in scripts (toasts, alerts) are read from the
// HTML source by copy/copy_inventory.py.
//
//   node strings.mjs <prototype.html> <out.txt>
//        [--containers "section.screen,[id$=Sheet],[id$=Scr],.sheet[id],[role=dialog]"]
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { chromiumPath, flags } from './chromium.mjs';

const [,, protoPath, outPath, ...rest] = process.argv;
if (!protoPath || !outPath) { console.error('usage: node strings.mjs <prototype.html> <out.txt>'); process.exit(2); }
const opt = flags(rest);
const containers = opt.containers ?? 'section.screen,[id$="Sheet"],[id$="Scr"],.sheet[id],[role="dialog"],[role="alertdialog"]';

const browser = await chromium.launch({ executablePath: chromiumPath(), headless: true });
const page = await (await browser.newContext({ viewport: { width: 402, height: 874 } })).newPage();
await page.goto('file://' + path.resolve(protoPath), { waitUntil: 'load' });
await page.waitForTimeout(500);
const out = await page.evaluate((containers) => {
  const blocks = [];
  document.querySelectorAll(containers).forEach(el => {
    const t = el.textContent.replace(/[ \t]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
    if (t) blocks.push('### ' + (el.id || el.className) + '\n' + t);
  });
  return blocks.join('\n\n');
}, containers);
fs.writeFileSync(outPath, out);
console.log(`${out.length} chars -> ${outPath}`);
await browser.close();
