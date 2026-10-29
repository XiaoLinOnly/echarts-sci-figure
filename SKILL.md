---
name: echarts-sci-figure
description: Publication-ready scientific figures with ECharts — profile the data, pick the most suitable or creatively substituted chart type, adapt a cached example, and render SVG or 600-dpi PNG with a colorblind-safe journal theme. Use for 科研绘图、论文配图、选图、图表类型选择、柱状图/折线图/散点图/雷达图/平行坐标/热图/桑基图/箱线图/森林图/凹凸图, journal-quality axis-based figures, or when the user asks which chart best fits their data or how to make a figure publication-ready.
---

# 科研 ECharts 出图

把一份数据变成可投稿的图，固定走六步：摸底 → 定候选 → 取示例 → 改写 → 渲染 → 自检。
选图规则在 `references/selection.md`，非常规替换在 `references/substitutions.md`，两者都要读。

本文件所在目录即 skill 根目录，下面记作 `$SKILL`。执行前先设置（Git Bash）：

```bash
SKILL="$HOME/.qoder-cn/skills/echarts-sci-figure"
```

## 适用范围

适用：坐标轴类（柱/点/折线/散点/误差棒/森林）、矩阵类（热图/相关/混淆）、高维（平行坐标/散点矩阵）、流与层级（桑基/和弦/矩形树/旭日）、分布概览（直方/箱线）。

不适用：小提琴图、raincloud、边际分布散点、显著性括号标注、LaTeX 字体一致性——这些走 `nature-figure` 或 matplotlib，不要硬用 ECharts 模拟。

## 第 1 步：摸底数据

```bash
python "$SKILL/scripts/profile_data.py" data.csv
python "$SKILL/scripts/profile_data.py" data.csv --json
```

输出列类型、缺失率、唯一值数、量纲跨度、`hints`（推荐图族）和 `warnings`。
拿到后先判断三件事：**谁是类别、谁是数值、有没有不确定度**。再判断数据是否含负值、是否时间序列、n 是否过小。
用户只给代码而不给数据文件时，读代码或问清列含义，不要凭空假设量纲。

## 第 2 步：定候选

按 `references/selection.md` 走四关：硬约束 → 数据形态 → A/B/C 三级候选 → 加权打分。
**默认给三个候选**（稳妥/更优/创意），每个写：为什么、代价、成立条件、对应示例 id。推荐项放第一。
用户已经明确要某种图时，仍要指出该图是否违反第 0 关硬约束；违反就直说，并给替代。
创意候选从 `references/substitutions.md` 里找，必须写明成立条件——不成立就不给。

## 第 3 步：取示例

```bash
python "$SKILL/scripts/find_example.py" -q 雷达
python "$SKILL/scripts/find_example.py" -q error --cached-only
python "$SKILL/scripts/find_example.py" -c sankey
python "$SKILL/scripts/find_example.py" --id boxplot-multi --show
```

索引含 377 个官方示例（34 类），常用示例已缓存在 `assets/examples/`（当前 41 个）。
`--cached-only` 命中就直接用缓存；没命中时按 id 下载：

```bash
python "$SKILL/scripts/update_examples.py" --id sankey-simple
```

想先看示例原貌，用原生画布预览：

```bash
node "$SKILL/scripts/render.mjs" ./assets/examples/radar.ts ./preview.png --unit px --width 700 --height 500
```

官方示例按 700×500 设计；直接缩到 85 mm 会让示例里写死的字号与 `radius` 失衡，所以先看原貌、再按第 4 步改写。

## 第 4 步：改写

```bash
node "$SKILL/scripts/new_option.mjs" bar-simple ./fig-option.mjs
```

生成的骨架把官方示例转成 `export default option`，之后把示例数据替换成真实数据。
`new_option.mjs` 会顺带把 TS 类型转成 JS、移除动画用的顶层定时器；依赖 `fetch`/`$.get`/`document` 的示例（option 不在模块顶层）会直接拒绝生成，这类示例用 `--show` 读结构后手写 option。

可直接使用挂载在全局的 `__FIG__` 助手：

| 字段 | 含义 |
| --- | --- |
| `__FIG__.widthPx` / `heightPx` / `widthMm` / `heightMm` | 画布尺寸（数值） |
| `__FIG__.pt(v)` | 磅 → 像素（字号用它，保证缩放后仍是目标 pt） |
| `__FIG__.mm(v)` | 毫米 → 像素（间距用） |
| `__FIG__.px(v)` | 原样返回，用于表达式统一 |
| `__FIG__.palette` | Okabe-Ito 色盲安全色板数组 |
| `__FIG__.fontFamily` | 当前主题字体串 |
| `__FIG__.ppt` / `ppmm` | 每磅 / 每毫米像素数 |

最小骨架：

```js
const fig = __FIG__;
const option = {
  xAxis: { type: 'category', name: '配方', data: ['A', 'B', 'C'] },
  yAxis: { type: 'value', name: '拉伸强度 (MPa)' },
  series: [{
    type: 'bar',
    data: [812, 795, 840],
    itemStyle: { color: fig.palette[0] },
    label: { show: true, position: 'top', fontSize: fig.pt(7) }
  }]
};
export default option;
```

改写要点：
- 轴标题必须带单位：`name: '拉伸强度 (MPa)'`，不要写 `'Strength'`
- 字号统一用 `fig.pt(7|8|9)`；不要写裸 `fontSize`
- 示例里写死的几何量（`radius: 80`、`barWidth: 30`、`center: ['25%','40%']`）是按 700×500 画布定的，缩到期刊栏宽时改成百分比或 `fig.mm()`
- 颜色只从 `fig.palette` 取，按类别顺序，不要每根柱换色
- 删掉交互组件（`dataZoom`、`toolbox`、`brush`）和示例自带标题——静态图里它们只会压住数据，标题交给图注
- 不确定度用 `custom` 系列的误差棒，或 `markLine`/`markArea` 画区间
- 中文标签直接用，主题已配置 `Microsoft YaHei` / `PingFang SC` 回退

## 第 5 步：渲染

```bash
node "$SKILL/scripts/render.mjs" ./fig-option.mjs ./fig.svg --width 85 --height 62
node "$SKILL/scripts/render.mjs" ./fig-option.mjs ./fig.png --width 85 --height 62 --dpi 600
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--width` / `--height` | 85 / 62 | 画布尺寸；`mm` 单位下就是期刊栏宽 |
| `--unit` | `mm` | `mm` 或 `px` |
| `--dpi` | 600 | 仅 PNG；600 适合线条图，300 适合含位图 |
| `--theme` | 内置 `theme-publication.mjs` | 自定义主题路径 |
| `--debug` | 关 | 打印堆栈与 ECharts 日志 |

渲染器自动做：关闭动画、白底、`containLabel`、坐标轴有 `name` 时自动放大边距、套用论文主题。
成功时打印 JSON：`{ok, format, output, width_px, height_px, bytes, warnings}`。
`warnings` 非空要读：通常是官方示例用了已废弃 API（如 `api.style`）或示例自身的弃用字段，不影响出图，但改写时应换成新写法。

常用尺寸：单栏 85×60、1.5 栏 114×75、双栏 174×110，单位 mm。

## 第 6 步：自检

出图后逐项确认，不通过就改：

- 尺寸与目标期刊栏宽一致，文字缩放后 7–9 pt
- 两个轴都有标题且带单位；刻度有效数字一致
- 没有标签重叠、图例压住数据、坐标轴被裁切
- 雷达/树/网络/桑基的标签不越出画布（长标签换行或缩短，必要时降 `radius`）
- 负值与零值处理正确；堆叠图不含负值
- 颜色 ≤8 种且来自 `fig.palette`；灰度下仍能区分系列
- 有不确定度的地方画了误差棒，图注写清 SD/SEM/95%CI
- 样本量 n 写在图注或轴标签里
- 矢量（SVG）优先；PNG 仅在其要求位图时使用

视觉核查：用 Read 直接看输出图。发现文字被裁、标签重叠、留白失衡时，调 `grid` 边距或 `--height`，不要靠缩字号解决。

## 目录

```
SKILL.md
references/selection.md        选图四关、形态→图族表、候选模板、打分、期刊约束
references/substitutions.md    25 组替换（含成立条件与反例）、三类高价值替换
references/theme-publication.mjs  Okabe-Ito 色板 + 论文主题
assets/index.json              377 个官方示例索引
assets/examples/*.ts           41 个已缓存示例源码
scripts/profile_data.py        CSV/TSV/JSON 数据画像
scripts/find_example.py        示例检索（关键词/类别/id）
scripts/new_option.mjs         示例 → 可渲染 option 骨架
scripts/render.mjs             SSR 渲染 SVG / PNG
scripts/update_examples.py     刷新索引、按 id 下载示例
```

## 依赖

`echarts` + `sharp` + `esbuild` 已装在 `$SKILL/node_modules`。换机器或缺失时：

```bash
cd "$SKILL" && npm install
```

Python 脚本只用标准库，无需安装。若 `sharp` 在目标平台装不上，SVG 输出仍可用（render.mjs 只在 PNG 分支加载 sharp）。
