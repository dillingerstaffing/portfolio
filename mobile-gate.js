// Mobile width gate for the portfolio build.
// Renders the built pages at a 390px phone viewport (headless Chromium,
// file:// URL, no network needed) and fails the build if anything lays out
// wider than the viewport. This is the mechanical backstop for the
// "no page-level horizontal scrolling" contract: a grid that collapses to
// a bare `1fr` column on mobile lets one wide child (e.g. a <pre> with long
// lines) stretch the track, and every paragraph in the article then wraps
// off-screen. Desktop CSS already carries minmax(0, 1fr) guards; this gate
// makes sure the mobile overrides keep them, no matter what content a
// future article adds.
//
// Usage: node mobile-gate.js <index.html> [post-page ...]
// Exit 0 when every checked width fits, 1 with a violation list otherwise.
// Set SKIP_MOBILE_GATE=1 to bypass (emergencies only; the bypass is loud).
const { spawn } = require('child_process');
const path = require('path');
const puppeteer = require('puppeteer-core');

const VIEWPORT_W = 390;
const TOLERANCE = 1; // sub-pixel rounding slack

function fail(lines) {
  console.error('MOBILE GATE FAILED: content wider than the 390px viewport:');
  for (const l of lines) console.error('  ' + l);
  process.exit(1);
}

async function launchChrome() {
  const chrome = '/opt/meta-chromium/chrome';
  const proc = spawn(chrome, [
    '--headless', '--no-sandbox', '--disable-gpu',
    '--remote-debugging-port=0', 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  const wsUrl = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('no DevTools URL from chrome')), 20000);
    let buf = '';
    proc.stderr.on('data', (d) => {
      buf += d.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
    proc.on('error', (e) => { clearTimeout(timer); reject(e); });
    proc.on('exit', () => { clearTimeout(timer); reject(new Error('chrome exited early')); });
  });
  return { proc, wsUrl };
}

async function checkPage(browser, file, isIndex) {
  const page = await browser.newPage();
  await page.emulate({
    viewport: { width: VIEWPORT_W, height: 844, isMobile: true, hasTouch: true },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  });
  const url = 'file://' + path.resolve(file) + (isIndex ? '#blog' : '');
  await page.goto(url, { waitUntil: 'load', timeout: 45000 });
  await new Promise((r) => setTimeout(r, 1200));
  const result = await page.evaluate((VW) => {
    const bad = [];
    const docSW = document.documentElement.scrollWidth;
    if (docSW > VW + 1) bad.push(`document scrollWidth ${docSW}px`);
    const scope = document.querySelector('#blog') || document;
    scope.querySelectorAll('article.research-note').forEach((art, i) => {
      const w = art.getBoundingClientRect().width;
      if (w > VW + 1) bad.push(`article.research-note[${i}] width ${Math.round(w)}px`);
      const body = art.querySelector('.research-body');
      if (body) {
        const bw = body.getBoundingClientRect().width;
        if (bw > VW + 1) bad.push(`article[${i}] .research-body width ${Math.round(bw)}px`);
        body.querySelectorAll('p').forEach((p, j) => {
          const pw = p.getBoundingClientRect().width;
          if (pw > VW + 1) bad.push(`article[${i}] p[${j}] width ${Math.round(pw)}px`);
        });
      }
    });
    return bad;
  }, VIEWPORT_W);
  await page.close();
  return result.map((l) => `${path.basename(file)}: ${l}`);
}

(async () => {
  if (process.env.SKIP_MOBILE_GATE === '1') {
    console.log('mobile gate: SKIPPED via SKIP_MOBILE_GATE=1');
    return;
  }
  const files = process.argv.slice(2);
  if (!files.length) {
    console.error('usage: node mobile-gate.js <index.html> [post-page ...]');
    process.exit(2);
  }
  let chromeProc = null;
  try {
    const { proc, wsUrl } = await launchChrome();
    chromeProc = proc;
    const browser = await puppeteer.connect({ browserWSEndpoint: wsUrl });
    const violations = [];
    for (let i = 0; i < files.length; i++) {
      violations.push(...await checkPage(browser, files[i], i === 0));
    }
    await browser.close();
    if (violations.length) fail(violations);
    console.log(`mobile gate: OK (${files.length} page(s) fit the 390px viewport)`);
  } catch (e) {
    console.error('mobile gate: ERROR ' + e.message);
    process.exit(1);
  } finally {
    if (chromeProc) chromeProc.kill('SIGKILL');
  }
})();
