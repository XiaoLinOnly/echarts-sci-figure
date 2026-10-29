#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as echarts from 'echarts';
import sharp from 'sharp';
import { transformSync } from 'esbuild';

const SKILL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PX_PER_MM = 96 / 25.4;
if (typeof echarts.setLogLevel === 'function') echarts.setLogLevel('error');

function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) {
      positional.push(a);
      continue;
    }
    const key = a.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) flags[key] = true;
    else {
      flags[key] = next;
      i++;
    }
  }
  return { positional, flags };
}

function fail(message, debug) {
  const payload = { ok: false, error: message };
  if (debug) payload.stack = new Error(message).stack;
  console.log(JSON.stringify(payload, null, 2));
  process.exit(1);
}

const { positional, flags } = parseArgs(process.argv.slice(2));
const debug = Boolean(flags.debug);
if (positional.length < 2) {
  fail('用法: node scripts/render.mjs <option.mjs|option.ts|option.json> <out.svg|out.png> [--width 85] [--height 62] [--unit mm|px] [--dpi 600]', debug);
}

const [inputPath, outputPath] = positional;
const unit = flags.unit === 'px' ? 'px' : 'mm';
const width = Number(flags.width ?? 85);
const height = Number(flags.height ?? Math.round(width * 0.62));
const dpi = Number(flags.dpi ?? 600);
if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
  fail('width/height 必须是正数', debug);
}

const widthPx = Math.max(1, Math.round(unit === 'mm' ? width * PX_PER_MM : width));
const heightPx = Math.max(1, Math.round(unit === 'mm' ? height * PX_PER_MM : height));
const widthMm = unit === 'mm' ? width : widthPx / PX_PER_MM;
const heightMm = unit === 'mm' ? height : heightPx / PX_PER_MM;

const themePath = path.resolve(String(flags.theme ?? path.join(SKILL_DIR, 'references', 'theme-publication.mjs')));
let themeMod;
try {
  themeMod = await import(pathToFileURL(themePath).href + `?t=${Date.now()}`);
} catch (e) {
  fail(`主题文件加载失败: ${themePath}: ${e.message}`, debug);
}
const theme = themeMod.default;
const palette = themeMod.palette ?? theme?.color ?? [];
const figureDefaults = themeMod.figureDefaults ?? {};

const fig = {
  unit,
  widthMm,
  heightMm,
  widthPx,
  heightPx,
  dpi,
  ppt: 96 / 72,
  ppmm: PX_PER_MM,
  pt: (v) => v * (96 / 72),
  mm: (v) => v * PX_PER_MM,
  px: (v) => v,
  palette,
  fontFamily: theme?.textStyle?.fontFamily
};
globalThis.__FIG__ = fig;
globalThis.echarts = echarts;

const warnings = [];

function stripExampleHeader(code) {
  return code.replace(/^\s*\/\*[\s\S]*?\*\/\s*/, '');
}

async function loadOption(file) {
  const ext = path.extname(file).toLowerCase();
  if (ext === '.json') {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  }
  if (ext === '.mjs' || ext === '.js') {
    const mod = await import(pathToFileURL(file).href + `?t=${Date.now()}`);
    const option = mod.default ?? mod.option;
    if (!option || typeof option !== 'object') throw new Error('模块必须 export default 一个 option 对象');
    return option;
  }
  if (ext === '.ts') {
    let code = stripExampleHeader(fs.readFileSync(file, 'utf8'));
    if (/^\s*import\s/m.test(code)) {
      throw new Error('该示例含 import 依赖，不能直接渲染；请另存为 .mjs 并补齐依赖或数据');
    }
    if (/\b(fetch|XMLHttpRequest)\s*\(|\$\.(getJSON|get|ajax)\s*\(/.test(code)) {
      throw new Error('该示例依赖远程数据（fetch/$.getJSON），请先把数据内联到 option 后再渲染');
    }
    if (/\b(document|window)\./.test(code)) {
      throw new Error('该示例含 DOM 操作，不能用于 SSR 渲染；请另存为纯 option 模块');
    }
    code = code.replace(/^\s*export\s*\{\s*\}\s*;?\s*$/gm, '');
    code = code.replace(/^\s*export\s+default\s+/m, 'option = ');
    const declaresOption = /(^|\n)\s*(let|const|var)\s+option\b/.test(code);
    let js;
    try {
      js = transformSync(code, { loader: 'ts', target: 'es2020', format: 'cjs', charset: 'utf8' }).code;
    } catch (e) {
      throw new Error(`示例 TypeScript 转换失败：${e.message}`);
    }
    const body = `${declaresOption ? '' : 'var option;'}\n${js}\nreturn option;`;
    try {
      const fn = new Function('echarts', '__FIG__', body);
      const option = fn(echarts, fig);
      if (!option || typeof option !== 'object') throw new Error('示例没有产生 option 对象');
      return option;
    } catch (e) {
      throw new Error(`示例转换失败（可能含 TS 语法）：${e.message}`);
    }
  }
  throw new Error(`不支持的输入格式: ${ext}`);
}

let option;
try {
  option = await loadOption(path.resolve(inputPath));
} catch (e) {
  fail(e.message, debug);
}

option.animation = false;
option.backgroundColor = option.backgroundColor ?? '#FFFFFF';
option.textStyle = { ...(theme?.textStyle ?? {}), ...(option.textStyle ?? {}) };
if (option.xAxis || option.yAxis) {
  option.grid = { ...(figureDefaults.grid ?? {}), ...(option.grid ?? {}) };
}
const axes = [].concat(option.xAxis ?? [], option.yAxis ?? []).flat();
if (axes.some((a) => a && typeof a === 'object' && a.name)) {
  const g = option.grid ?? {};
  const bump = (v, min) => (Number.isFinite(Number(v)) ? Math.max(Number(v), min) : v ?? min);
  option.grid = {
    ...g,
    left: bump(g.left, 36),
    right: bump(g.right, 16),
    top: bump(g.top, 28),
    bottom: bump(g.bottom, 34),
    containLabel: true
  };
}
if (option.tooltip && option.tooltip.show !== true) option.tooltip.show = false;

echarts.registerTheme('publication', theme);

let chart;
const originalWarn = console.warn;
console.warn = (...args) => {
  const msg = args.map(String).join(' ');
  if (/DEPRECATED/i.test(msg)) {
    warnings.push(msg.replace(/^\[ECharts\]\s*/, ''));
    return;
  }
  originalWarn.apply(console, args);
};
try {
  chart = echarts.init(null, 'publication', {
    renderer: 'svg',
    ssr: true,
    width: widthPx,
    height: heightPx
  });
  chart.setOption(option, { notMerge: true });
  let svg = chart.renderToSVGString();
  if (!svg.startsWith('<?xml')) svg = `<?xml version="1.0" encoding="UTF-8"?>\n${svg}`;
  fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
  const out = path.resolve(outputPath);
  const ext = path.extname(out).toLowerCase();
  if (ext === '.png') {
    const svgDensity = dpi * 72 / 96;
    const buffer = await sharp(Buffer.from(svg), { density: svgDensity })
      .withMetadata({ density: dpi })
      .png({ compressionLevel: 9 })
      .toFile(out);
    console.log(JSON.stringify({
      ok: true,
      format: 'png',
      output: out,
      width_px: buffer.width,
      height_px: buffer.height,
      bytes: buffer.size,
      warnings
    }, null, 2));
  } else {
    fs.writeFileSync(out, svg, 'utf8');
    console.log(JSON.stringify({
      ok: true,
      format: 'svg',
      output: out,
      width_px: widthPx,
      height_px: heightPx,
      bytes: Buffer.byteLength(svg),
      warnings
    }, null, 2));
  }
} catch (e) {
  fail(`渲染失败: ${e.message}`, debug);
} finally {
  console.warn = originalWarn;
  if (chart) chart.dispose();
}
