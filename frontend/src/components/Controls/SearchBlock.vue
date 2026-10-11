<template>
	<div ref="searchBlock" class="focus-within:outline-none" @keydown="handleKeydown">
		<div v-if="!builderStore.readOnlyMode" class="mb-4">
			<OptionToggle
				v-model="searchMode"
				:options="[
					{ label: __('Search'), value: 'search', icon: 'lucide-search' },
					{ label: __('Find & Replace'), value: 'replace', icon: 'lucide-edit-3' },
				]" />
		</div>

		<div class="mb-4 flex gap-2">
			<BuilderInput
				ref="searchInput"
				class="flex-1"
				type="text"
				:placeholder="searchMode === 'replace' ? __('Find...') : __('Search blocks...')"
				v-model="query"
				@input="setQuery" />

			<Popover bare>
				<template #trigger="{ open }">
					<Button
						icon="lucide-filter"
						:label="__('Filters')"
						:class="[
							'flex items-center gap-2 text-sm',
							selectedFiltersCount > 0 ? 'border-ink-gray-6 bg-ink-gray-1' : '',
						]">
						<span
							v-if="selectedFiltersCount > 0"
							class="bg-ink-gray-7 ml-1 rounded-full px-2 py-0.5 text-xs text-white">
							{{ selectedFiltersCount }}
						</span>
						<span
							:class="[open ? 'lucide-chevron-up' : 'lucide-chevron-down', 'size-4']"
							aria-hidden="true" />
					</Button>
				</template>
				<template #default>
					<div class="w-48 rounded-6 bg-surface-base py-2 shadow-lg ring-1 ring-black ring-opacity-5">
						<div class="text-xs-medium px-3 py-2 text-ink-gray-5">{{ __("Filter search results by:") }}</div>
						<div class="space-y-1 px-2">
							<label
								v-for="filter in filters"
								:key="filter.name"
								class="flex cursor-pointer items-center rounded-4 px-2 py-1.5 text-sm text-ink-gray-8 hover:bg-surface-gray-1">
								<Checkbox
									:modelValue="filter.selected"
									@update:modelValue="toggleFilter(filter)"
									class="mr-3" />
								<span>{{ filter.name }}</span>
							</label>
						</div>
						<div class="border-surface-gray-3 mt-1 border-t px-2 pt-2">
							<Button @click="clearAllFilters" variant="subtle" class="w-full">
								{{ __("Clear all filters") }}
							</Button>
						</div>
					</div>
				</template>
			</Popover>
		</div>

		<div v-if="canvasStore.activeCanvas?.selectedBlocks?.length" class="mb-4">
			<label class="flex cursor-pointer items-center text-sm text-ink-gray-7">
				<Checkbox v-model="searchInSelectedBlock" class="mr-2" />
				<span>{{ __("Search inside selected block only") }}</span>
			</label>
		</div>

		<div v-if="searchMode === 'replace'" class="mb-4">
			<BuilderInput
				class="w-full"
				type="text"
				:placeholder="__('Replace with...')"
				v-model="replaceQuery"
				@keydown.enter="handlePrimaryAction" />
		</div>

		<div
			v-if="query && (searchMode === 'search' || (searchMode === 'replace' && results.length > 0))"
			class="mb-4">
			<Button
				v-if="searchMode === 'replace'"
				@click="handlePrimaryAction"
				variant="solid"
				class="w-full"
				:disabled="!replaceableCount">
				{{ __("Replace All ({0} matches)", [replaceableCount]) }}
			</Button>
			<div v-if="searchMode === 'replace' && replacedCount > 0" class="mt-2 text-xs text-ink-gray-5">
				{{
					replacedCount === 1
						? __("Replaced in {0} block", [replacedCount])
						: __("Replaced in {0} blocks", [replacedCount])
				}}
			</div>
		</div>

		<div v-if="!query" class="mt-6 text-center">
			<div class="flex flex-col items-center justify-center py-8">
				<div class="mb-4 flex size-16 items-center justify-center rounded-full bg-surface-gray-2">
					<span class="lucide-search size-8 text-ink-gray-4" aria-hidden="true" />
				</div>
				<h3 class="text-sm-medium mb-2 text-ink-gray-6">{{ __("Search your blocks") }}</h3>
			</div>
		</div>

		<div v-else-if="results.length > 0" class="max-h-64 overflow-y-auto">
			<!-- Search Results -->
			<div v-for="result in results" :key="result.blockId">
				<div
					class="mb-2 flex cursor-pointer items-center justify-between rounded-4 px-3 py-2 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
					@mouseover.stop="canvasStore.activeCanvas?.setHoveredBlock(result.blockId)"
					@click="canvasStore.selectBlock(result, null, true, true)">
					<div class="line-clamp-2 flex-1">
						{{ result.getBlockDescription() }}
						<div class="mt-1 text-xs text-ink-gray-5">
							{{ getMatchDetails(result) }}
						</div>
					</div>
					<Button
						v-if="searchMode === 'replace'"
						@click.stop="replaceInBlocks([result])"
						variant="subtle"
						class="ml-3 px-2 py-1 text-xs">
						{{ __("Replace") }}
					</Button>
				</div>
			</div>
		</div>

		<div v-else-if="query && results.length === 0" class="mt-6 text-center">
			<!-- No Results State -->
			<div class="flex flex-col items-center justify-center py-6">
				<span class="lucide-search mb-3 size-6 text-ink-gray-4" aria-hidden="true" />
				<h3 class="text-sm-medium mb-1 text-ink-gray-6">{{ __("No results found") }}</h3>
				<p class="text-xs text-ink-gray-5">{{ __("Try different keywords or adjust your filters") }}</p>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { watchDebounced } from "@vueuse/core";
import { Checkbox, Popover } from "frappe-ui";
import { computed, nextTick, onMounted, Ref, ref, shallowRef, watch } from "vue";
import { toast } from "frappe-ui";
import OptionToggle from "./OptionToggle.vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const searchBlock = ref(null) as Ref<HTMLInputElement | null>;
const searchInput = ref(null) as Ref<HTMLInputElement | null>;
const query = ref("");
const replaceQuery = ref("");
const searchMode = ref<"search" | "replace">("search");
const replacedCount = ref(0);
const results = ref([]) as Ref<Block[]>;
const blockMatches = shallowRef(new Map<string, SearchMatch[]>());
const searchInSelectedBlock = ref(false);

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

const replaceableCount = computed(
	() => [...blockMatches.value.values()].flat().filter((match) => match.set).length,
);

const setQuery = (value: string) => {
	query.value = value;
	replacedCount.value = 0;
};

const handlePrimaryAction = () => {
	if (searchMode.value === "replace" && results.value.length > 0) {
		replaceInBlocks(getScopeBlocks());
	}
};

const handleKeydown = (event: KeyboardEvent) => {
	// Cmd+F or Ctrl+F for quick search
	if ((event.metaKey || event.ctrlKey) && event.key === "f") {
		event.preventDefault();
		const input = searchInput.value?.querySelector?.("input") || searchInput.value;
		if (input && "focus" in input && typeof input.focus === "function") {
			input.focus();
		}
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

const clearAllFilters = () => {
	filters.value.forEach((filter) => {
		filter.selected = false;
	});
};

const getMatchDetails = (block: Block) => {
	const labels = new Set(blockMatches.value.get(block.blockId)?.map((match) => match.label));
	return labels.size ? __("Found in: {0}", [[...labels].join(", ")]) : "";
};

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
	replacedCount.value += changedBlocks.length;
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
	const blocks: Block[] = [];

	function addBlock(block: Block) {
		blocks.push(block);
		block.children?.forEach((child) => addBlock(child));
	}

	const selectedBlocks = canvasStore.activeCanvas?.selectedBlocks;
	const startingBlock =
		searchInSelectedBlock.value && selectedBlocks?.length
			? selectedBlocks[0]
			: canvasStore.activeCanvas?.getRootBlock();

	if (startingBlock) {
		addBlock(startingBlock);
	}

	return blocks;
};

const searchWithFilters = (searchTerm: string): Block[] => {
	const searchResults: Block[] = [];
	const matchesByBlock = new Map<string, SearchMatch[]>();
	const limit = 50;

	// every match is kept so the Replace All count covers blocks past the display limit
	for (const block of getScopeBlocks()) {
		const matches = collectMatches(block, searchTerm);
		if (!matches.length) continue;
		matchesByBlock.set(block.blockId, matches);
		if (searchResults.length < limit) searchResults.push(block);
	}

	blockMatches.value = matchesByBlock;
	return searchResults;
};

onMounted(async () => {
	await nextTick();
	const input = searchInput.value?.querySelector?.("input") || searchInput.value;
	if (input && "focus" in input && typeof input.focus === "function") {
		input.focus();
	}
});

// edits, deletions, replaces, undo and redo all move the undo stack's head (its length stops
// changing once the stack is full); searching never edits blocks, so it can't retrigger itself
watchDebounced(
	[
		query,
		() => filters.value.map((f) => f.selected).join(","),
		searchMode,
		searchInSelectedBlock,
		() => canvasStore.activeCanvas?.getRootBlock(),
		() => canvasStore.activeCanvas?.history?.undoStack[0],
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

// Reset replaced count when switching modes
watchDebounced(
	searchMode,
	() => {
		replacedCount.value = 0;
	},
	{ debounce: 100 },
);
</script>
