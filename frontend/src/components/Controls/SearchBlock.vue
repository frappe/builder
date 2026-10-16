<template>
	<div class="flex flex-col gap-2" @keydown="handleKeydown">
		<div class="flex items-center gap-1.5">
			<div class="min-w-0 flex-1">
				<BuilderInput
					ref="searchInput"
					type="text"
					:placeholder="__('Find')"
					v-model="query"
					@input="(value: string) => (query = value)" />
			</div>
			<Popover bare>
				<template #trigger>
					<Button icon="lucide-list-filter" :label="__('Filters')" :tooltip="__('Filters')" />
				</template>
				<template #default>
					<div class="w-44 rounded-6 border border-outline-gray-2 bg-surface-base p-1 shadow-xl">
						<div class="text-xs-medium px-2 py-1.5 text-ink-gray-5">{{ __("Filters") }}</div>
						<label
							v-for="filter in filters"
							:key="filter.key"
							class="flex cursor-pointer items-center gap-2 rounded-4 px-2 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-2">
							<Checkbox v-model="filter.selected" />
							{{ filter.name }}
						</label>
						<div class="mt-1 border-t border-outline-gray-1 pt-1">
							<Button
								variant="ghost"
								class="w-full"
								:label="__('Clear all filters')"
								:disabled="!selectedFilters.length"
								@click="clearFilters" />
						</div>
					</div>
				</template>
			</Popover>
		</div>

		<div v-if="searchMode === 'replace'" class="flex items-center gap-1.5">
			<!-- BuilderInput passes class to its inner input, so the wrapper sizes it -->
			<div class="min-w-0 flex-1">
				<BuilderInput
					ref="replaceInput"
					type="text"
					:placeholder="__('Replace with')"
					v-model="replaceQuery"
					@input="(value: string) => (replaceQuery = value)" />
			</div>
			<Button
				:label="__('Replace All')"
				:disabled="!matchCount.matches"
				@click="replaceInBlocks(getScopeBlocks())" />
		</div>

		<div v-if="selectedFilters.length" class="flex flex-wrap gap-1">
			<Button
				v-for="filter in selectedFilters"
				:key="filter.key"
				size="sm"
				iconRight="lucide-x"
				:label="filter.name"
				@click="filter.selected = false" />
		</div>

		<label
			v-if="canvasStore.activeCanvas?.selectedBlocks?.length || searchInSelectedBlock"
			class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-7">
			<Checkbox v-model="searchInSelectedBlock" />
			{{ __("Search inside selected block only") }}
		</label>

		<p v-if="!query" class="text-sm text-ink-gray-5">
			{{ __("Find text, styles, attributes and classes") }}
		</p>

		<template v-else>
			<div class="flex min-h-7 items-center justify-between gap-2 border-t border-outline-gray-1 pt-2">
				<span class="text-sm text-ink-gray-5">{{ matchSummary }}</span>
				<Button
					v-if="results.length"
					variant="ghost"
					:icon="allCollapsed ? 'lucide-chevrons-up-down' : 'lucide-chevrons-down-up'"
					:label="allCollapsed ? __('Expand All') : __('Collapse All')"
					:tooltip="allCollapsed ? __('Expand All') : __('Collapse All')"
					@click="toggleAllCollapsed" />
			</div>

			<div
				v-if="results.length"
				ref="resultList"
				class="-mx-1 max-h-80 overflow-y-auto"
				:class="{
					'[mask-image:linear-gradient(to_bottom,black_calc(100%_-_2rem),transparent)]': !arrivedState.bottom,
				}"
				@mouseleave="canvasStore.activeCanvas?.setHoveredBlock(null)">
				<div
					v-for="result in results"
					:key="result.blockId"
					class="group cursor-pointer rounded-4 pb-1 hover:bg-surface-gray-2"
					@mouseover.stop="canvasStore.activeCanvas?.setHoveredBlock(result.blockId)"
					@click="canvasStore.selectBlock(result, null, true, true)">
					<div class="flex h-7 items-center gap-1.5 px-1">
						<span
							:class="[
								isCollapsed(result) ? 'lucide-chevron-right' : 'lucide-chevron-down',
								'size-3 shrink-0 text-ink-gray-4',
							]"
							aria-hidden="true"
							@click.stop="toggleCollapsed(result)" />
						<span :class="[result.getIcon(), 'size-3 shrink-0 text-ink-gray-5']" aria-hidden="true" />
						<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">
							{{ result.getBlockDescription() }}
						</span>
						<span
							class="mr-1 min-w-5 rounded-full bg-surface-gray-2 px-1.5 text-center text-xs text-ink-gray-6 group-hover:bg-surface-gray-3"
							:class="{ 'group-hover:hidden': searchMode === 'replace' }">
							{{ blockMatches.get(result.blockId)?.length }}
						</span>
						<Button
							v-if="searchMode === 'replace'"
							class="hidden group-hover:inline-flex"
							variant="ghost"
							icon="lucide-replace"
							:label="__('Replace')"
							:tooltip="__('Replace in this block')"
							@click.stop="replaceInBlocks([result])" />
					</div>
					<template v-if="!isCollapsed(result)">
						<div
							v-for="(preview, index) in getPreviews(result)"
							:key="index"
							class="truncate py-0.5 pl-10 pr-2 text-xs text-ink-gray-7">
							<span v-if="preview.label" class="mr-1.5 text-ink-gray-5">{{ preview.label }}</span>
							<span>{{ preview.before }}</span>
							<mark class="rounded-sm bg-surface-amber-2 text-ink-gray-9">{{ preview.hit }}</mark>
							<span>{{ preview.after }}</span>
						</div>
					</template>
				</div>
			</div>

			<p v-else class="text-xs text-ink-gray-5">{{ __("Try different keywords or adjust your filters") }}</p>

			<p v-if="blockMatches.size > results.length" class="text-xs text-ink-gray-5">
				{{ __("Showing {0} of {1} blocks", [results.length, blockMatches.size]) }}
			</p>
		</template>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { getBlocksInScope } from "@/utils/block/tree";
import { useScroll, watchDebounced } from "@vueuse/core";
import { Checkbox, Popover } from "frappe-ui";
import { computed, nextTick, onMounted, onUnmounted, Ref, ref, shallowRef, unref, watch } from "vue";
import type { ComponentPublicInstance } from "vue";
import { toast } from "frappe-ui";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const searchInput = ref<ComponentPublicInstance | null>(null);
const replaceInput = ref<ComponentPublicInstance | null>(null);
const resultList = ref<HTMLElement | null>(null);
const { arrivedState, measure } = useScroll(resultList);
const collapsedBlockIds = ref(new Set<string>());
const query = ref("");
const replaceQuery = ref("");
// owned by PageBuilder, whose popup header holds the Find / Replace tabs
const searchMode = defineModel<"search" | "replace">("mode", { default: "search" });
const blockMatches = shallowRef(new Map<string, SearchMatch[]>());
// every match is kept so the Replace All count covers blocks past the display limit
const results = computed(() =>
	[...blockMatches.value.values()].slice(0, 50).map((matches) => matches[0].block),
);
// ids captured when scope is ticked, so clicking results doesn't move it and undo brings deleted blocks back
const scopeBlockIds = ref<string[]>([]);
const searchInSelectedBlock = computed({
	get: () => scopeBlockIds.value.length > 0,
	set: (scoped: boolean) => {
		const selectedBlocks: Block[] = scoped ? canvasStore.activeCanvas?.selectedBlocks || [] : [];
		scopeBlockIds.value = selectedBlocks.map((block) => block.blockId);
	},
});

type SearchLocation = {
	// text content goes unlabelled, it's what most searches are after
	label?: string;
	value: unknown;
	exact?: boolean;
	// returns false when it rejects the value
	set?: (value: string) => unknown;
};

type SearchMatch = SearchLocation & { block: Block; value: string };

// keeps fontWeight: 600 a number when the replaced value is still numeric
const restoreType = (original: unknown, value: string) =>
	typeof original === "number" && value.trim() !== "" && !isNaN(Number(value)) ? Number(value) : value;

// the canvas throws while rendering a block whose tag isn't a valid element name
const isTagName = (value: string) => /^[a-z][a-z0-9-]*$/i.test(value);

const styleLocations = (styles: BlockStyleMap, breakpoint?: string): SearchLocation[] =>
	Object.entries(styles)
		// __last_display and friends are editor state, not styles
		.filter(([style]) => !style.startsWith("__"))
		.map(([style, value]) => ({
			label: breakpoint ? `${style} (${breakpoint})` : style,
			value,
			set: (newValue: string) => {
				if (newValue === "") delete styles[style as styleProperty];
				else styles[style as styleProperty] = restoreType(value, newValue);
			},
		}));

const attributeLocations = (attributes: BlockAttributeMap): SearchLocation[] =>
	Object.entries(attributes).map(([attribute, value]) => ({
		label: attribute,
		value,
		set: (newValue: string) => (attributes[attribute] = restoreType(value, newValue)),
	}));

const textLocations = (block: Block): SearchLocation[] => {
	const innerHTML = block.getInnerHTML();
	if (!innerHTML) return [];
	// unlike DOMParser, a template keeps a leading <script>/<style> in place, and nothing in it runs
	const template = document.createElement("template");
	template.innerHTML = innerHTML;
	const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT);
	const locations: SearchLocation[] = [];
	while (walker.nextNode()) {
		const node = walker.currentNode as Text;
		if (node.parentElement?.closest("script, style")) continue;
		locations.push({
			value: node.data,
			set: (value: string) => {
				node.data = value;
				block.setInnerHTML(template.innerHTML);
			},
		});
	}
	return locations;
};

const searchFields: { key: string; name: string; locations: (block: Block) => SearchLocation[] }[] = [
	{
		key: "element",
		name: __("Tag"),
		locations: (block) => [
			{
				label: __("Tag"),
				value: block.getElement(),
				exact: true,
				// the root's tag is fixed, the Tag control hides it too
				set: block.isRoot()
					? undefined
					: (value: string) => isTagName(value) && (block.element = value.toLowerCase()),
			},
		],
	},
	{
		key: "data",
		name: __("Data"),
		locations: (block) =>
			[block.dataKey, ...block.getDynamicValues()].map((dataKey) => ({
				label: dataKey?.property ? `${__("Data")} (${dataKey.property})` : __("Data"),
				value: dataKey?.key,
				set: (value: string) =>
					dataKey === block.dataKey
						? block.setDataKey("key", value)
						: dataKey?.type &&
							block.setDynamicValue(dataKey.property, dataKey.type, value, dataKey.comesFrom),
			})),
	},
	{ key: "content", name: __("Content"), locations: textLocations },
	{
		key: "styles",
		name: __("Style"),
		locations: (block) => [
			...styleLocations(block.baseStyles),
			...styleLocations(block.tabletStyles, __("Tablet")),
			...styleLocations(block.mobileStyles, __("Mobile")),
		],
	},
	{
		key: "attributes",
		name: __("Attributes"),
		locations: (block) => [
			...attributeLocations(block.attributes),
			...attributeLocations(block.customAttributes),
		],
	},
	{
		key: "classes",
		name: __("CSS Classes"),
		locations: (block) =>
			(block.classes || []).map((className) => ({
				label: __("Class"),
				value: className,
				set: (value: string) =>
					(block.classes = block.classes.map((c) => (c === className ? value : c)).filter(Boolean)),
			})),
	},
];

const filters = ref(
	searchFields.map((h) => ({
		name: h.name,
		selected: false,
		key: h.key,
	})),
);

const selectedFilters = computed(() => filters.value.filter((f) => f.selected));

const clearFilters = () => filters.value.forEach((filter) => (filter.selected = false));

const matchCount = computed(() => ({
	matches: [...blockMatches.value.values()].flat().length,
	blocks: blockMatches.value.size,
}));

const matchSummary = computed(() => {
	const { matches, blocks } = matchCount.value;
	if (!matches) return __("No matches");
	if (matches === 1) return __("1 match");
	if (blocks === 1) return __("{0} matches in 1 block", [matches]);
	return __("{0} matches in {1} blocks", [matches, blocks]);
});

const focusInput = (input: Ref<ComponentPublicInstance | null>) =>
	input.value?.$el.querySelector("input")?.focus();

const focusFind = () => focusInput(searchInput);

const isCollapsed = (block: Block) => collapsedBlockIds.value.has(block.blockId);

const toggleCollapsed = (block: Block) => {
	if (!collapsedBlockIds.value.delete(block.blockId)) collapsedBlockIds.value.add(block.blockId);
};

const allCollapsed = computed(() => results.value.length > 0 && results.value.every(isCollapsed));

const toggleAllCollapsed = () => {
	collapsedBlockIds.value = new Set(allCollapsed.value ? [] : results.value.map((block) => block.blockId));
};

const handleKeydown = (event: KeyboardEvent) => {
	// Cmd+F or Ctrl+F for quick search
	if ((event.metaKey || event.ctrlKey) && event.key === "f") {
		event.preventDefault();
		focusFind();
	}
	// Escape to clear search
	if (event.key === "Escape") {
		query.value = "";
		replaceQuery.value = "";
	}
};

const getPreviews = (block: Block) =>
	(blockMatches.value.get(block.blockId) || []).map((match) => {
		const collapse = (text: string) => text.replace(/\s+/g, " ");
		// the matches can trail the query by the search debounce, so the term may be missing
		const index = match.value.toLowerCase().indexOf(query.value.toLowerCase());
		if (index < 0) return { label: match.label, before: collapse(match.value), hit: "", after: "" };
		const start = Math.max(0, index - 16);
		const end = index + query.value.length;
		return {
			label: match.label,
			before: (start ? "…" : "") + collapse(match.value.slice(start, index)).trimStart(),
			hit: match.value.slice(index, end),
			after: collapse(match.value.slice(end)),
		};
	});

const activeFields = computed(() => {
	const activeFilterKeys = selectedFilters.value.map((f) => f.key);
	return activeFilterKeys.length
		? searchFields.filter((f) => activeFilterKeys.includes(f.key))
		: searchFields;
});

const collectMatches = (block: Block, searchTerm: string): SearchMatch[] => {
	const term = searchTerm.toLowerCase();
	return activeFields.value.flatMap((field) =>
		field
			.locations(block)
			.filter(({ value }) => typeof value === "string" || typeof value === "number")
			.map((location) => ({ ...location, block, value: String(location.value) }))
			.filter(({ value, exact }) =>
				exact ? value.toLowerCase() === term : value.toLowerCase().includes(term),
			),
	);
};

const escapeRegExp = (string: string) => {
	return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
};

const replaceInBlocks = (blocks: Block[]) => {
	if (builderStore.readOnlyMode || !query.value) return;

	const matches = blocks.flatMap((block) => collectMatches(block, query.value)).filter((match) => match.set);
	if (!matches.length) {
		toast.error(__("No replacements made"));
		return;
	}

	const regex = new RegExp(escapeRegExp(query.value), "gi");
	const history = canvasStore.activeCanvas?.history;
	const pauseId = history?.pause();
	let replaced: SearchMatch[] = [];
	try {
		// a function replacement keeps "$" in the replace text literal
		replaced = matches.filter(
			(match) => match.set?.(match.value.replace(regex, () => replaceQuery.value)) !== false,
		);
	} finally {
		nextTick(() => {
			if (pauseId) history?.resume(pauseId, replaced.length > 0, true);
		});
	}

	if (!replaced.length) {
		toast.error(__("No replacements made"));
		return;
	}
	const changedBlocks = [...new Set(replaced.map((match) => match.block))];
	toast.success(
		changedBlocks.length === 1
			? __("Replaced in {0}", [changedBlocks[0].getBlockDescription()])
			: __("Replaced in {0} blocks", [changedBlocks.length]),
	);
};

const performSearch = () => {
	blockMatches.value = query.value ? searchWithFilters(query.value) : new Map();
};

const getScopeBlocks = (): Block[] => {
	const rootBlock = canvasStore.activeCanvas?.getRootBlock();
	return rootBlock ? getBlocksInScope(rootBlock, scopeBlockIds.value) : [];
};

const searchWithFilters = (searchTerm: string) => {
	const matchesByBlock = new Map<string, SearchMatch[]>();
	for (const block of getScopeBlocks()) {
		// replace mode lists only what Replace can change
		const matches = collectMatches(block, searchTerm).filter(
			(match) => searchMode.value === "search" || match.set,
		);
		if (matches.length) matchesByBlock.set(block.blockId, matches);
	}
	return matchesByBlock;
};

// the native autofocus attribute only fires once per page, so it would miss every reopen
onMounted(() => nextTick(focusFind));

onUnmounted(() => canvasStore.activeCanvas?.setHoveredBlock(null));

watchDebounced(
	[
		query,
		selectedFilters,
		searchMode,
		scopeBlockIds,
		() => canvasStore.activeCanvas?.getRootBlock(),
		() => unref(canvasStore.activeCanvas?.history?.undoStack)?.[0],
	],
	performSearch,
	{ debounce: 300 },
);

watch(searchMode, (mode) => {
	if (mode === "replace") nextTick(() => focusInput(replaceInput));
});

// arrivedState only updates on scroll, so the bottom fade needs a fresh measure when the list changes
watch([results, () => collapsedBlockIds.value.size], () => measure(), { flush: "post" });

// the panel can stay open while a version preview loads, so drop out of replace mode
watch(
	() => builderStore.readOnlyMode,
	(readOnly) => {
		if (readOnly) searchMode.value = "search";
	},
	{ immediate: true },
);
</script>
