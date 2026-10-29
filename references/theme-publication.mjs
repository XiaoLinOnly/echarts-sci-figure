const FONT = "Arial, 'Helvetica Neue', 'Microsoft YaHei', 'PingFang SC', sans-serif";

export const palette = [
  '#0072B2',
  '#E69F00',
  '#009E73',
  '#D55E00',
  '#CC79A7',
  '#56B4E9',
  '#F0E442',
  '#000000'
];

const axisCommon = {
  axisLine: { show: true, lineStyle: { color: '#333333', width: 1 } },
  axisTick: { show: true, lineStyle: { color: '#333333', width: 1 } },
  axisLabel: { color: '#1A1A1A', fontSize: 11, fontFamily: FONT },
  nameTextStyle: { color: '#1A1A1A', fontSize: 11, fontFamily: FONT },
  splitLine: { show: false }
};

export default {
  color: palette,
  backgroundColor: '#FFFFFF',
  textStyle: { fontFamily: FONT, fontSize: 12, color: '#1A1A1A' },
  title: {
    textStyle: { fontSize: 13, fontWeight: 'normal', color: '#111111', fontFamily: FONT },
    subtextStyle: { fontSize: 11, color: '#444444', fontFamily: FONT }
  },
  legend: {
    icon: 'roundRect',
    itemWidth: 10,
    itemHeight: 8,
    itemGap: 8,
    textStyle: { fontSize: 11, color: '#1A1A1A', fontFamily: FONT }
  },
  categoryAxis: {
    ...axisCommon,
    splitLine: { show: false },
    axisTick: { show: true, alignWithLabel: true, lineStyle: { color: '#333333', width: 1 } }
  },
  valueAxis: {
    ...axisCommon,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: true, lineStyle: { color: '#E6E6E6', width: 1, type: 'solid' } }
  },
  logAxis: {
    ...axisCommon,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: true, lineStyle: { color: '#E6E6E6', width: 1, type: 'solid' } }
  },
  timeAxis: {
    ...axisCommon,
    splitLine: { show: true, lineStyle: { color: '#E6E6E6', width: 1, type: 'solid' } }
  },
  line: { symbol: 'circle', symbolSize: 5, lineStyle: { width: 1.6 }, smooth: false },
  bar: { barMaxWidth: 22, itemStyle: { borderWidth: 0 } },
  scatter: { symbolSize: 8, itemStyle: { opacity: 0.85 } },
  pie: { itemStyle: { borderColor: '#FFFFFF', borderWidth: 1 } },
  tooltip: { show: false }
};

export const figureDefaults = {
  grid: { left: 8, right: 8, top: 16, bottom: 8, containLabel: true },
  animation: false
};
