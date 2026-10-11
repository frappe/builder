<template>
	<div class="flex flex-col gap-2" @keydown="handleKeydown">
		<OptionToggle
			v-if="!builderStore.readOnlyMode"
			v-model="searchMode"
			:options="[
				{ label: __('Search'), value: 'search' },
				{ label: __('Replace'), value: 'replace' },
			]" />

		<div class="flex gap-1.5">
			<BuilderInput
				ref="searchInput"
				class="flex-1"
				type="text"
				:placeholder="__('Find')"
				v-model="query"
				@input="setQuery">
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</BuilderInput>
			<Popover bare>
				<template #trigger>
					<Button
						icon="lucide-list-filter"
						:label="__('Filters')"
						:variant="selectedFiltersCount ? 'subtle' : 'ghost'" />
				</template>
				<template #default>
					<div class="w-44 rounded-6 border border-outline-gray-2 bg-surface-base p-1 shadow-xl">
						<label
							v-for="filter in filters"
							:key="filter.key"
							class="flex cursor-pointer items-center gap-2 rounded-4 px-2 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-2">
							<Checkbox :modelValue="filter.selected" @update:modelValue="toggleFilter(filter)" />
							{{ filter.name }}
						</label>
					</div>
				</template>
			</Popover>
		</div>

		<BuilderInput
			v-if="searchMode === 'replace'"
			type="text"
			:placeholder="__('Replace with')"
			v-model="replaceQuery"
			@input="(value: string) => (replaceQuery = value)">
			<template #prefix>
				<span class="lucide-corner-down-right size-4 text-ink-gray-5" aria-hidden="true" />
			</template>
		</BuilderInput>

		<div v-if="selectedFiltersCount" class="flex flex-wrap gap-1">
			<Button
				v-for="filter in filters.filter((f) => f.selected)"
				:key="filter.key"
				size="sm"
				iconRight="lucide-x"
				:label="filter.name"
				@click="toggleFilter(filter)" />
		</div>

		<label
			v-if="canvasStore.activeCanvas?.selectedBlocks?.length || searchInSelectedBlock"
			class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-7">
			<Checkbox v-model="searchInSelectedBlock" />
			{{ __("Search inside selected block only") }}
		</label>

		<p v-if="!query" class="py-2 text-sm text-ink-gray-5">
			{{ __("Find text, styles, attributes and classes") }}
		</p>

		<template v-else>
			<div class="flex min-h-7 items-center justify-between gap-2 border-t border-outline-gray-1 pt-2">
				<span class="text-sm text-ink-gray-5">{{ matchSummary }}</span>
				<Button
					v-if="searchMode === 'replace'"
					variant="solid"
					:label="__('Replace All')"
					:disabled="!matchCount.matches"
					@click="replaceInBlocks(getScopeBlocks())" />
			</div>

			<div
				v-if="results.length"
				class="-mx-1 max-h-72 overflow-y-auto"
				@mouseleave="canvasStore.activeCanvas?.setHoveredBlock(null)">
				<div
					v-for="result in results"
					:key="result.blockId"
					class="group flex cursor-pointer items-start gap-2 rounded-4 px-2 py-1.5 hover:bg-surface-gray-2"
					@mouseover.stop="canvasStore.activeCanvas?.setHoveredBlock(result.blockId)"
					@click="canvasStore.selectBlock(result, null, true, true)">
					<span :class="[result.getIcon(), 'mt-0.5 size-3.5 shrink-0 text-ink-gray-5']" aria-hidden="true" />
					<div class="min-w-0 flex-1">
						<div class="truncate text-sm text-ink-gray-8">{{ result.getBlockDescription() }}</div>
						<div
							v-for="(preview, index) in getPreviews(result)"
							:key="index"
							class="truncate text-xs text-ink-gray-5">
							<span class="mr-1 text-ink-gray-6">{{ preview.label }}</span>
							<span>{{ preview.before }}</span>
							<mark class="rounded-sm bg-surface-amber-2 text-ink-gray-9">{{ preview.hit }}</mark>
							<span>{{ preview.after }}</span>
						</div>
						<div v-if="getHiddenMatchCount(result)" class="text-xs text-ink-gray-4">
							{{ __("+{0} more", [getHiddenMatchCount(result)]) }}
						</div>
					</div>
					<Button
						v-if="searchMode === 'replace'"
						class="invisible shrink-0 group-hover:visible"
						variant="ghost"
						icon="lucide-replace"
						:label="__('Replace')"
						:tooltip="__('Replace in this block')"
						@click.stop="replaceInBlocks([result])" />
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
import { watchDebounced } from "@vueuse/core";
import { Checkbox, Popover } from "frappe-ui";
import { computed, nextTick, onMounted, onUnmounted, Ref, ref, shallowRef, unref, watch } from "vue";
import type { ComponentPublicInstance } from "vue";
import { toast } from "frappe-ui";
import OptionToggle from "./OptionToggle.vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const searchInput = ref<ComponentPublicInstance | null>(null);
const query = ref("");
const replaceQuery = ref("");
const searchMode = ref<"search" | "replace">("search");
const results = ref([]) as Ref<Block[]>;
const blockMatches = shallowRef(new Map<string, SearchMatch[]>());
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
	label: string;
	value: unknown;
	exact?: boolean;
	set?: (value: string) => void;
};

type SearchMatch = SearchLocation & { block: Block; value: string };

// keeps fontWeight: 600 a number when the replaced value is still numeric
const restoreType = (original: unknown, value: string) =>
	typeof original === "number" && value.trim() !== "" && !isNaN(Number(value)) ? Number(value) : value;

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
			label: __("Content"),
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
		locations: (block) => [{ label: __("Tag"), value: block.getElement(), exact: true }],
	},
	{
		key: "data",
		name: __("Data"),
		locations: (block) =>
			[block.dataKey, ...block.getDynamicValues()].map((dataKey) => ({
				label: dataKey?.property ? `${__("Data")} (${dataKey.property})` : __("Data"),
				value: dataKey?.key,
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

const selectedFiltersCount = computed(() => {
	return filters.value.filter((f) => f.selected).length;
});

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

const setQuery = (value: string) => {
	query.value = value;
};

const focusFind = () => searchInput.value?.$el.querySelector("input")?.focus();

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

const toggleFilter = (filter: any) => {
	filter.selected = !filter.selected;
};

const PREVIEWS_PER_BLOCK = 2;

const getPreviews = (block: Block) =>
	(blockMatches.value.get(block.blockId) || []).slice(0, PREVIEWS_PER_BLOCK).map((match) => {
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

const getHiddenMatchCount = (block: Block) =>
	Math.max(0, (blockMatches.value.get(block.blockId)?.length || 0) - PREVIEWS_PER_BLOCK);

const activeFields = () => {
	const activeFilterKeys = filters.value.filter((f) => f.selected).map((f) => f.key);
	return activeFilterKeys.length
		? searchFields.filter((f) => activeFilterKeys.includes(f.key))
		: searchFields;
};

const collectMatches = (block: Block, searchTerm: string): SearchMatch[] => {
	const term = searchTerm.toLowerCase();
	return activeFields().flatMap((field) =>
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
	try {
		// a function replacement keeps "$" in the replace text literal
		matches.forEach((match) => match.set?.(match.value.replace(regex, () => replaceQuery.value)));
	} finally {
		// the history watcher fires after this returns; resuming right away would record an extra empty step
		nextTick(() => {
			if (pauseId) history?.resume(pauseId, true);
		});
	}

	const changedBlocks = [...new Set(matches.map((match) => match.block))];
	toast.success(
		changedBlocks.length === 1
			? __("Replaced in {0}", [changedBlocks[0].getBlockDescription()])
			: __("Replaced in {0} blocks", [changedBlocks.length]),
	);
};

const performSearch = () => {
	results.value = [];
	if (query.value) {
		const filteredBlocks = searchWithFilters(query.value);
		if (filteredBlocks?.length) {
			results.value = filteredBlocks;
		}
	}
};

const getScopeBlocks = (): Block[] => {
	const rootBlock = canvasStore.activeCanvas?.getRootBlock();
	return rootBlock ? getBlocksInScope(rootBlock, scopeBlockIds.value) : [];
};

const searchWithFilters = (searchTerm: string): Block[] => {
	const searchResults: Block[] = [];
	const matchesByBlock = new Map<string, SearchMatch[]>();
	const limit = 50;

	// every match is kept so the Replace All count covers blocks past the display limit
	for (const block of getScopeBlocks()) {
		// replace mode lists only what Replace can change
		const matches = collectMatches(block, searchTerm).filter(
			(match) => searchMode.value === "search" || match.set,
		);
		if (!matches.length) continue;
		matchesByBlock.set(block.blockId, matches);
		if (searchResults.length < limit) searchResults.push(block);
	}

	blockMatches.value = matchesByBlock;
	return searchResults;
};

// the native autofocus attribute only fires once per page, so it would miss every reopen
onMounted(() => nextTick(focusFind));

onUnmounted(() => canvasStore.activeCanvas?.setHoveredBlock(null));

// edits, deletions, replaces, undo and redo all move the undo stack's head (its length stops
// changing once the stack is full); searching never edits blocks, so it can't retrigger itself.
// history sits in a ref, so undoStack arrives unwrapped despite its Ref type
watchDebounced(
	[
		query,
		() => filters.value.map((f) => f.selected).join(","),
		searchMode,
		scopeBlockIds,
		() => canvasStore.activeCanvas?.getRootBlock(),
		() => unref(canvasStore.activeCanvas?.history?.undoStack)?.[0],
	],
	performSearch,
	{ debounce: 300 },
);

// the panel can stay open while a version preview loads, so drop out of replace mode
watch(
	() => builderStore.readOnlyMode,
	(readOnly) => {
		if (readOnly) searchMode.value = "search";
	},
	{ immediate: true },
);
</script>
