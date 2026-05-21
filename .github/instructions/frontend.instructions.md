---
description: "Use when writing, editing, or reviewing Vue components, TypeScript, Pinia stores, composables, Tailwind styling, or frappe-ui data resources in the frontend/ folder. Covers component patterns, state management, API calls, imports, and code style."
applyTo: "frontend/**"
---

# Frontend Conventions — Frappe Builder

## Stack

- **Vue 3.5** — Composition API only; `<script setup lang="ts">` in every component
- **TypeScript** — strict mode; interfaces in `frontend/src/types/Builder/`
- **Pinia** — state management (6 domain stores)
- **frappe-ui** — UI components + reactive data resources
- **Tailwind CSS v3** — frappe-ui preset + `@tailwindcss/container-queries`
- **Vite** — build tool; `@` alias maps to `frontend/src/`

---

## Imports

Always use the `@` alias. Never use `../` relative imports across directory boundaries.

```typescript
// ✅ correct
import useBuilderStore from "@/stores/builderStore";
import type { BuilderPage } from "@/types/Builder/BuilderPage";
import { getBlockInstance } from "@/utils/helpers";

// ❌ wrong
import useBuilderStore from "../../stores/builderStore";
```

---

## Component Structure

Use `<script setup lang="ts">` always. Order: `<script setup>` → `<template>` → `<style scoped>`.

```vue
<script setup lang="ts">
import { ref, computed } from "vue";
import useBuilderStore from "@/stores/builderStore";

const store = useBuilderStore();
const count = ref(0);
const doubled = computed(() => count.value * 2);
</script>

<template>
	<div class="flex items-center gap-2">
		<span>{{ doubled }}</span>
	</div>
</template>
```

- No Options API, no `defineComponent()` wrapper
- Props: use `defineProps<{ ... }>()` with TypeScript generics
- Emits: use `defineEmits<{ ... }>()` with TypeScript generics

---

## TypeScript

- **Strict mode is on** — annotate all function params and return types
- **Interfaces** (not `type` aliases) for domain objects → `frontend/src/types/Builder/`
- **Union types** for modes and fixed sets: `type BuilderMode = "select" | "text" | "component"`
- Use `// @ts-expect-error` only for known library quirks, with a comment explaining why

```typescript
// ✅ Good — interface in types/Builder/
interface BuilderPage {
	name: string;
	route: string;
	published: 0 | 1;
}

// ✅ Good — annotated function
function getPageTitle(page: BuilderPage): string {
	return page.page_title ?? page.route;
}
```

---

## Reactive Data Patterns

| Pattern | When to use |
|---------|------------|
| `ref()` | Primitives, single values, template refs |
| `reactive()` | Plain objects where you always access via the object |
| `computed()` | Derived / calculated values |
| `watch()` | Side effects triggered by a specific dependency |
| `watchEffect()` | Auto-tracked side effects |

```typescript
const mode = ref<BuilderMode>("select");
const blockData = reactive({ id: "", styles: {} });
const isEditable = computed(() => mode.value !== "preview");

watch(() => route.params.pageId, async (pageId) => {
	await pageStore.fetchActivePage(String(pageId));
});
```

---

## State Management (Pinia)

All shared state lives in a Pinia store. Do not use `provide/inject` or component-local state for data used across components.

**Existing stores** (do not duplicate their concerns):
| Store | Concern |
|-------|---------|
| `builderStore` | Global UI state: mode, panels, dark mode, realtime |
| `pageStore` | Active page: blocks tree, page metadata, save/load |
| `canvasStore` | Canvas viewport: zoom, pan, breakpoint, selection |
| `blockStore` | Block UID registry and block data map |
| `componentStore` | Component library cache |

**Store pattern**:
```typescript
const useMyStore = defineStore("myStore", {
	state: () => ({
		value: <MyType>null,
	}),
	getters: {
		derivedValue(): boolean {
			return !!this.value;
		},
	},
	actions: {
		async loadData(id: string) {
			this.value = await fetchSomething(id);
		},
	},
});
export default useMyStore;
```

Use `useStorage` from `@vueuse/core` for state that should persist across reloads.

---

## Data Fetching — frappe-ui Resources

Never use raw `axios` or `fetch`. Always use frappe-ui resource helpers.

```typescript
import { createListResource, createDocumentResource, createResource } from "frappe-ui";

// List of docs
const webPages = createListResource({
	doctype: "Builder Page",
	fields: ["name", "route", "page_title", "published"],
	filters: { is_template: 0 },
	cache: "pages",           // Redis cache key (omit if data changes frequently)
	pageLength: 50,
});

// Single document
const settingsDoc = createDocumentResource({
	doctype: "Builder Settings",
	name: "Builder Settings",
	auto: true,
});

// Custom API call
const previewResource = createResource({
	url: "builder.builder.doctype.builder_page.builder_page.get_page_preview_html",
	method: "POST",
	auto: false,
});
await previewResource.fetch({ page: pageName });
```

- `resource.data` — the response
- `resource.loading` — boolean
- `resource.error` — error state
- Call `.fetch()` / `.submit()` to trigger manually when `auto: false`

---

## UI Components — frappe-ui

Use frappe-ui components instead of building from scratch.

```vue
<template>
	<Button variant="solid" @click="save">Save</Button>
	<FormControl type="text" v-model="title" label="Page Title" />
	<Popover placement="bottom">
		<template #target="{ togglePopover }">
			<Button @click="togglePopover">Open</Button>
		</template>
		<template #body>Content</template>
	</Popover>
</template>
```

**Notifications**: `toast.success("Saved!")`, `toast.error("Failed")`

**Telemetry**: Use `useTelemetry()` from `frappe-ui/frappe` to `capture()` events.

---

## Tailwind CSS

Uses frappe-ui Tailwind preset. Custom token names:
- Colors: `surface-white`, `ink-gray-*` (100–900), `outline-gray-*`
- Typography scale: `text-p-xs`, `text-p-sm`, `text-p-base`, `text-p-xl`, `text-p-2xl`
- Container queries enabled via `@tailwindcss/container-queries`

```vue
<!-- ✅ correct — use frappe-ui tokens, sorted classes (prettier enforces order) -->
<div class="flex h-screen w-full flex-col gap-4 bg-surface-white p-4">
	<h1 class="text-p-2xl font-semibold text-ink-gray-900">Title</h1>
</div>
```

**Prettier auto-sorts Tailwind classes** — do not manually order them.

---

## Composables (Custom Hooks)

Composables live in `frontend/src/utils/use*.ts`. Existing composables to reuse:

| Hook | Purpose |
|------|---------|
| `useCanvasUtils` | Zoom, pan, scroll-into-view |
| `useCanvasHistory` | Undo/redo |
| `useBlockSelection` | Multi-select, selection state |
| `useCanvasEvents` | Keyboard + mouse event handlers |
| `useCanvasDropZone` | Drag-drop target detection |
| `useDraggableBlock` | Block drag logic |
| `useShortcut` | Keyboard shortcuts |
| `useAnalytics` | Analytics data + chart config |

New composables should return an object (not a class), be pure (no side effects in setup), and be named `use<Feature>.ts`.

---

## Router

Three routes only — do not add routes without good reason:
- `/` — Dashboard
- `/page/:pageId` — Editor
- `/page/:pageId/preview` — Preview

All routes use `beforeEnter: validateVisit` to check auth/permissions. Dynamic imports are mandatory for route components (code splitting):

```typescript
component: () => import("@/pages/PageBuilder.vue")
```

---

## Code Style

Enforced by Prettier + ESLint (run `yarn lint`):

- **Tabs** for indentation (not spaces)
- **Double quotes** (`"`) everywhere
- `printWidth: 110`
- `trailingComma: "all"`
- `bracketSameLine: true` — closing `>` on same line as last attribute

```typescript
// ✅ correct style
function handleBlockClick(block: Block, event: MouseEvent): void {
	const store = useBuilderStore();
	store.mode = "select";
}
```

---

## Performance

Performance is a core product value — not optional. Profile before and after any change that touches rendering, reactivity, or data loading.

### Reactivity budget
- Don't make deeply nested objects reactive if only shallow access is needed — use `shallowRef()` or `markRaw()` for large inert objects (e.g., editor instances, canvas state)
- Use `toRaw()` before passing reactive objects into non-Vue contexts (DOM APIs, workers, serialization)
- Avoid `watch` with `deep: true` on large objects; use targeted watchers on specific keys

### Component rendering
- **`v-if` over `v-show`** for components that are rarely visible — don't mount what isn't shown
- Use `v-once` for truly static sub-trees
- Prefer `v-memo` for list items that only need to re-render when specific deps change
- **Lazy-load all route components** with dynamic `import()` — no synchronous top-level imports of page components

### Data fetching
- Always set `cache: "<key>"` on `createListResource` for data that doesn't change per-user or per-session
- Batch list requests — use `filters: { name: ["in", ids] }` not repeated `createDocumentResource` calls in a loop
- Keep `pageLength` on list resources — never fetch unbounded lists

### Bundle size
- Chunk size warning limit is **1500KB** — stay well under it
- Tree-shake: `import { specificThing } from "library"` not `import * as lib from "library"`
- Audit any new dependency with `yarn build --report` before merging

### Main thread
- No synchronous blocking during user interactions — defer heavy work with `nextTick()` or `requestAnimationFrame()`
- Canvas zoom/pan uses `requestAnimationFrame` — don't add synchronous DOM reads inside animation loops
