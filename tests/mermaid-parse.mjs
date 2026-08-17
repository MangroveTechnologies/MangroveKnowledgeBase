// Parse every mermaid block in a markdown file. A broken diagram renders as an error box on
// GitHub rather than failing anything, so it is checked here instead.
//
//   npm install mermaid jsdom && node tests/mermaid-parse.mjs docs/architecture/README.md
//
// mermaid.parse() reaches for a DOM even to parse, which is what the jsdom shim is for.
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

// mermaid.parse() reaches for a DOM (DOMPurify) even when it only has to parse.
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.DOMPurify = (await import('dompurify')).default(dom.window);

const mermaid = (await import('mermaid')).default;
const md = readFileSync(process.argv[2], 'utf8');
const blocks = [...md.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m => m[1]);
mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
let bad = 0;
for (const [i, b] of blocks.entries()) {
  try {
    await mermaid.parse(b);
    console.log(`  block ${i + 1}: ok`);
  } catch (e) {
    bad++;
    console.log(`  block ${i + 1}: FAILED — ${String(e.message).split('\n').slice(0, 5).join(' | ')}`);
  }
}
console.log(bad ? `${bad} block(s) do not parse` : 'all blocks parse');
process.exit(bad ? 1 : 0);
