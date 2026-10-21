# Host modules

A trusted extension imports `builder`, `vue`, `pinia` and `frappe-ui` by their bare names. The editor page's import map resolves each name to one of these modules, so an extension shares the editor's own instances.

| File                             | Bare name   | What it gives                                                                                   |
| -------------------------------- | ----------- | ----------------------------------------------------------------------------------------------- |
| [`builder.ts`](./builder.ts)     | `builder`   | The editor API: the surface registries, the stores, `blockController`, `Block` and `lucideIcon` |
| [`vue.ts`](./vue.ts)             | `vue`       | The editor's Vue                                                                                |
| [`pinia.ts`](./pinia.ts)         | `pinia`     | The editor's pinia                                                                              |
| [`frappe-ui.ts`](./frappe-ui.ts) | `frappe-ui` | The editor's frappe-ui                                                                          |

`frontend/vite/hostModules.mjs` makes each file a build entry and writes the import map.

Only what `builder.ts` exports is reachable from an extension. A change to an export breaks extensions, so keep `frontend/extension-sdk/types/builder.d.ts` in step with it.

To write an extension, read [the SDK guide](../../extension-sdk/README.md).
