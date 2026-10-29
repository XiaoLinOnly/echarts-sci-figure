# echarts-sci-figure

把一份数据变成能投稿的图。基于 Apache ECharts 的科研绘图 skill：**摸底 → 定候选 → 取示例 → 改写 → 渲染 → 自检**，固定六步，每一步都有对应的脚本或文档。

适用场景是"这张数据到底该画什么图"和"画出来的图能不能进论文"，不是"给我一个图表库的 demo"。

## 它多做的一件事：选图

大多数人卡住的不是不会写 ECharts option，而是**选错图**。所以这个 skill 先做约束再做美观：

- 硬约束（第 0 关）：三维图、截断的柱轴、彩虹色阶、用饼图表达 8 个以上类别——直接否决，并给出替代
- 数据形态（第 1 关）：类别 / 数值 / 时间 / 不确定度四类先分清
- 三档候选（第 2 关）：稳妥 / 更优 / 创意，每档写清"为什么、代价是什么、成立条件"，推荐项放第一
- 加权打分（第 3 关）：准确性 40% > 可读性 30% > 信息密度 15% > 新颖度 15%

"创意"不是随便换图型。`references/substitutions.md` 收录了 28 组替换（柱状图→棒棒糖、折线→凹凸图、饼图→矩形树、矩阵→和弦……），每一组都写明**成立条件**和**反例**；条件不成立就不该用。

## 六步做什么

| 步骤 | 做什么 | 对应 |
|---|---|---|
| 1. 摸底 | 列类型、缺失率、量纲跨度，给出推荐图族与告警 | `scripts/profile_data.py` |
| 2. 定候选 | 三档候选 + 打分，指出是否违反硬约束 | `references/selection.md` |
| 3. 取示例 | 从 377 个官方示例里检索，命中缓存直接用 | `scripts/find_example.py` |
| 4. 改写 | 示例 → `export default option` 骨架，再换成真实数据 | `scripts/new_option.mjs` |
| 5. 渲染 | SSR 出 SVG 或 600 dpi PNG，套论文主题 | `scripts/render.mjs` |
| 6. 自检 | 字号、单位、重叠、裁切、色盲安全、不确定度 | `SKILL.md` 第 6 节 |

## 安装

作为 Qoder / Claude 风格的 skill 安装：

```bash
npx skills add -a qoder-cn XiaoLinOnly/echarts-sci-figure
```

或者直接 clone 到 skills 目录：

```bash
git clone https://github.com/XiaoLinOnly/echarts-sci-figure.git \
  ~/.qoder-cn/skills/echarts-sci-figure
```

然后装渲染依赖（`node_modules` 不入库）：

```bash
cd ~/.qoder-cn/skills/echarts-sci-figure && npm install
```

依赖是 `echarts` + `esbuild` + `sharp`。Python 脚本只用标准库。若 `sharp` 装不上，SVG 输出仍然可用——渲染器只在 PNG 分支加载它。

## 一次真实出图

CFRP 两种铺层相对准各向同性 `[0/±45/90]s` 基准的性能画像，5 个指标归一化到基准 = 100%。

| 指标 | `[0/90]s` | `[±45]s` |
|---|---|---|
| 拉伸强度 | 109 | 77 |
| 弹性模量 | 112 | 69 |
| 断裂伸长率 | 71 | 127 |
| 层间剪切 | 87 | 110 |
| 冲击韧性 | 66 | 135 |

```bash
# 3. 取示例
python scripts/find_example.py -q 雷达 --cached-only

# 4. 生成骨架，然后改成自己的数据和几何量
node scripts/new_option.mjs radar-multiple ./radar-layup.mjs

# 5. 渲染
node scripts/render.mjs ./radar-layup.mjs ./radar-layup.svg --width 90 --height 80
node scripts/render.mjs ./radar-layup.mjs ./radar-layup.png --width 90 --height 80 --dpi 600
```

option 的关键取舍（完整版见交付物）：

```js
const fig = __FIG__;
const option = {
  radar: {
    center: ['50%', '48%'],   // 不用写死半径，按画布百分比
    radius: '66%',
    axisNameGap: fig.mm(1.5), // 间距用 mm，缩放后不跑位
    indicator: [...]
  },
  series: [
    // 每个铺层单独一个 series：per-data-item 的 symbol 在 radar 上不生效
    { type: 'radar', symbol: 'circle',  lineStyle: { color: fig.palette[0], width: 1.5 }, ... },
    { type: 'radar', symbol: 'diamond', lineStyle: { color: fig.palette[1], width: 1.5 }, ... },
    // 100% 基准线：灰色虚线，silent 不可交互
    { type: 'radar', symbol: 'none', silent: true,
      lineStyle: { color: '#666666', width: 0.9, type: [5, 4] }, ... }
  ]
};
export default option;
```

产出 90 × 80 mm、600 dpi（2125 × 1888 px）的 PNG 与同尺寸 SVG，标签不裁切、灰度下两条曲线可分。

## `__FIG__` 助手

渲染时全局挂载，用来把"按 700×500 画布写死"的示例几何量换算到期刊栏宽：

| 字段 | 含义 |
|---|---|
| `pt(v)` | 磅 → 像素，字号统一用它 |
| `mm(v)` | 毫米 → 像素，间距用它 |
| `palette` | Okabe-Ito 色盲安全色板 |
| `widthMm` / `heightMm` | 当前画布尺寸 |

## 目录

```
SKILL.md                         六步流程本体
references/selection.md          选图四关、形态→图族表、候选模板、期刊约束
references/substitutions.md      28 组替换（含成立条件与反例）
references/theme-publication.mjs Okabe-Ito 色板 + 论文主题
assets/index.json                377 个官方示例索引
assets/examples/*.ts             41 个已缓存示例源码
scripts/profile_data.py          CSV/TSV/JSON 数据画像
scripts/find_example.py          示例检索（关键词 / 类别 / id）
scripts/new_option.mjs           示例 → 可渲染 option 骨架
scripts/render.mjs               SSR 渲染 SVG / PNG
scripts/update_examples.py       刷新索引、按 id 下载示例
```

## 什么不该用它做

小提琴图、raincloud、边际分布散点、显著性括号标注、LaTeX 字体一致性——这些用 ECharts 硬凑只会得到一个像论文图的图。走 `nature-figure`（matplotlib / ggplot2）或直接 matplotlib。

同理，雷达图只在"≤4 个对象、≥3 个维度、且已归一化"时成立；要排名或比大小，用点图或条形图。

## 第三方素材

`assets/examples/` 与 `assets/index.json` 来自 Apache ECharts 官方示例（Apache-2.0），署名见 [NOTICE.md](NOTICE.md)。

## 许可证

本仓库自身代码暂未指定开源许可证。在补上 LICENSE 之前，默认按"保留所有权利"处理——可以阅读和参考，但未授予复制、修改或再分发的许可。
