# Third-party notices

## Apache ECharts examples

`assets/examples/*.ts` and the metadata in `assets/index.json` are derived from
the Apache ECharts examples repository
(<https://github.com/apache/echarts-examples>), Copyright the Apache Software
Foundation, licensed under the Apache License 2.0
(<https://www.apache.org/licenses/LICENSE-2.0>).

They are vendored here as cached reference material so the skill can adapt an
official example offline, and are refreshed by `scripts/update_examples.py`.
Local modifications are limited to TypeScript type annotations and the
`export default option` wrapper applied at render time.
