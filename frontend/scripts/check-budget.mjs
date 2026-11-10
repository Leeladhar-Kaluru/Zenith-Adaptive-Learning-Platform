// Fails the build when the app grows past its speed budget. Run after `npm run build`.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const ENTRY_GZIP_MAX = 130 * 1024;     // entry JavaScript, gzip
const PRECACHE_MAX = 650 * 1024;       // everything installed by the service worker on first visit

const assets = readdirSync(join(dist, 'assets'));
const entry = assets.find((f) => /^index-.*\.js$/.test(f));
if (!entry) { console.error('Entry bundle not found'); process.exit(2); }
const entryGzip = gzipSync(readFileSync(join(dist, 'assets', entry))).length;

const sw = readFileSync(join(dist, 'sw.js'), 'utf8');
const urls = [...new Set([...sw.matchAll(/url:"([^"]+)"/g)].map((m) => m[1]))];
let precache = 0;
for (const u of urls) { try { precache += statSync(join(dist, u)).size; } catch { /* generated, not on disk */ } }

const fmt = (n) => `${(n / 1024).toFixed(1)} kB`;
console.log(`entry JS gzip   ${fmt(entryGzip)} (max ${fmt(ENTRY_GZIP_MAX)})`);
console.log(`first precache  ${fmt(precache)} in ${urls.length} files (max ${fmt(PRECACHE_MAX)})`);
let bad = false;
if (entryGzip > ENTRY_GZIP_MAX) { console.error('FAIL: entry bundle is over budget'); bad = true; }
if (precache > PRECACHE_MAX) { console.error('FAIL: service worker precache is over budget'); bad = true; }
process.exit(bad ? 1 : 0);
