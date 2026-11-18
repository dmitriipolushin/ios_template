// Finds a Chromium for playwright-core without downloading one: $PARITY_CHROMIUM, else the
// newest build in the Playwright cache (macOS arm64/x64, Linux). Undefined lets playwright-core
// try its own default.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export function chromiumPath() {
  if (process.env.PARITY_CHROMIUM) return process.env.PARITY_CHROMIUM;
  const caches = [
    path.join(os.homedir(), 'Library/Caches/ms-playwright'),
    path.join(os.homedir(), '.cache/ms-playwright'),
  ];
  const rels = [
    'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-mac/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
    'chrome-linux/chrome',
  ];
  for (const base of caches) {
    if (!fs.existsSync(base)) continue;
    const dirs = fs.readdirSync(base)
      .filter(d => /^chromium-\d+$/.test(d))
      .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]));
    for (const d of dirs) for (const rel of rels) {
      const p = path.join(base, d, rel);
      if (fs.existsSync(p)) return p;
    }
  }
  return undefined;
}

/** Command-line flags after the positional arguments: --name value / --flag. */
export function flags(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const key = argv[i].slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith('--')) out[key] = true;
    else { out[key] = next; i++; }
  }
  return out;
}
