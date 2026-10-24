# Host modules

A trusted plugin imports `builder`, `vue`, `pinia` and `frappe-ui` by their bare names. The editor page's import map resolves each name to one of these modules, so a plugin shares the editor's own instances.

| File                             | Bare name   | What it gives                                                                                   |
| -------------------------------- | ----------- | ----------------------------------------------------------------------------------------------- |
| [`builder.ts`](./builder.ts)     | `builder`   | The editor API: the surface registries, the stores, `blockController`, `Block` and `lucideIcon` |
| [`vue.ts`](./vue.ts)             | `vue`       | The editor's Vue                                                                                |
| [`pinia.ts`](./pinia.ts)         | `pinia`     | The editor's pinia                                                                              |
| [`frappe-ui.ts`](./frappe-ui.ts) | `frappe-ui` | The editor's frappe-ui                                                                          |

Every other module under `src/` is reachable as `builder/internal/<path>`, with no promise: a `.ts` module drops its suffix, and a `.vue` module keeps it. `main.ts` is left out, because it would start a second app.

`frontend/vite/hostModules.mjs` makes each module a build entry and writes the import map. An entry per module would make the bundler split the editor much more finely, so the editor would load several times as many files at startup. So the plugin first runs a quiet build without the internal entries, and pins each module to the chunk that build gives it. Each internal entry then only re-exports from the editor's usual chunks, and the editor loads what it loaded before.

`builder.ts` is the stable surface. A change to its exports breaks plugins, so keep `frontend/plugin-sdk/types/builder.d.ts` in step with it.

To write a plugin, read [the SDK guide](../../plugin-sdk/README.md).
