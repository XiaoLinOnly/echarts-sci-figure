#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { transformSync } from 'esbuild';

const SKILL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [id, out] = process.argv.slice(2);
if (!id || !out) {
  console.error('用法: node scripts/new_option.mjs <example-id> <out.mjs|out.ts>');
  process.exit(1);
}

const index = JSON.parse(fs.readFileSync(path.join(SKILL_DIR, 'assets', 'index.json'), 'utf8'));
const item = index.examples.find((e) => e.id === id);
if (!item) {
  console.error(`索引中没有 id: ${id}`);
  process.exit(1);
}
const srcPath = path.join(SKILL_DIR, item.file);
if (!fs.existsSync(srcPath)) {
  console.error(`示例未缓存: ${srcPath}\n先运行: python scripts/update_examples.py --id ${id}`);
  process.exit(1);
}

let code = fs.readFileSync(srcPath, 'utf8');
const notes = [];
if (/^\s*import\s/m.test(code)) notes.push('原示例含 import 依赖，需手工补齐或改为内联数据。');
const remote = /\b(fetch|XMLHttpRequest)\s*\(|\$\.(getJSON|get|ajax)\s*\(/.test(code);
const dom = /\b(document|window)\./.test(code);
if (remote || dom) {
  const why = remote ? '依赖远程数据，option 不在模块顶层' : '含 DOM 操作，option 依赖浏览器实例';
  console.error(JSON.stringify({
    ok: false,
    error: `该示例${why}，无法自动生成可渲染骨架。用 find_example.py --id ${id} --show 读结构后手写 option。`
  }, null, 2));
  process.exit(1);
}

code = code.replace(/^\s*\/\*[\s\S]*?\*\//, '');
code = code.replace(/^\s*export\s*\{\s*\}\s*;?\s*$/gm, '');
if (!/(^|\n)\s*(let|const|var)\s+option\b/.test(code)) {
  code = code.replace(/(^|\n)\s*option\s*=/, '$1const option =');
}

// 动画演示用的顶层定时器在静态图里没有意义，直接摘掉
function stripTopLevelTimers(source) {
  const re = /(^|\n)(setInterval|setTimeout)\s*\(/g;
  let removed = 0;
  let outCode = source;
  let m;
  while ((m = re.exec(outCode))) {
    const start = m.index + m[1].length;
    let i = outCode.indexOf('(', start);
    let depth = 0;
    let quote = null;
    for (; i < outCode.length; i++) {
      const c = outCode[i];
      if (quote) {
        if (c === '\\') i++;
        else if (c === quote) quote = null;
        continue;
      }
      if (c === '"' || c === "'" || c === '`') quote = c;
      else if (c === '(') depth++;
      else if (c === ')' && --depth === 0) {
        i++;
        break;
      }
    }
    outCode = outCode.slice(0, start) + outCode.slice(i);
    removed++;
    re.lastIndex = start;
  }
  return { code: outCode, removed };
}
const timers = stripTopLevelTimers(code);
code = timers.code;
if (timers.removed) notes.push(`已移除 ${timers.removed} 处顶层 setInterval/setTimeout 动画块。`);

let js;
try {
  js = transformSync(code, { loader: 'ts', target: 'es2020', format: 'esm', charset: 'utf8' }).code;
} catch (e) {
  notes.push(`TypeScript 转换失败，已原样输出：${e.message}`);
  js = code;
}
if (/\bmyChart\./.test(js)) notes.push('仍引用 myChart 实例，需要删掉该段或改成静态数据。');

const header = [
  `// Source: https://echarts.apache.org/examples/zh/editor.html?c=${id}`,
  `// ${item.titleCN || item.title} (${item.id})`,
  ...notes.map((n) => `// NOTE: ${n}`),
  '// Helpers: const { pt, mm, palette } = globalThis.__FIG__;',
  ''
].join('\n');

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
fs.writeFileSync(path.resolve(out), `${header}${js.trim()}\n\nexport default option;\n`, 'utf8');
console.log(JSON.stringify({ ok: true, output: path.resolve(out), warnings: notes }, null, 2));
