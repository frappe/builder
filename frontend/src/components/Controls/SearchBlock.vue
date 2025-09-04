<template>
	<div ref="searchBlock">
		<div class="mb-4 flex gap-2">
			<BuilderInput
				class="flex-1"
				type="text"
				:placeholder="searchMode === 'replace' ? 'Find...' : 'Search'"
				v-model="query"
				@input="setQuery" />
			<BuilderButton
				@click="toggleSearchMode"
				:variant="searchMode === 'replace' ? 'solid' : 'outline'"
				icon="repeat"
				:title="
					searchMode === 'replace' ? 'Switch to Search mode' : 'Switch to Find & Replace mode'
				"></BuilderButton>
		</div>

		<BuilderInput
			v-if="searchMode === 'replace'"
			class="mb-4"
			type="text"
			placeholder="Replace with..."
			v-model="replaceQuery" />

		<div class="mb-4 flex flex-wrap gap-2 text-sm">
			<Badge
				v-for="filter in filters"
				:key="filter.name"
				:label="filter.name"
				theme="gray"
				:variant="filter.selected ? 'solid' : 'outline'"
				size="sm"
				class="cursor-pointer"
				@click="toggleFilter(filter)" />
		</div>

		<div v-if="searchMode === 'replace' && results.length > 0" class="mb-4 space-y-3">
			<BuilderButton @click="replaceAll" variant="solid" class="w-full" :disabled="!replaceQuery">
				Replace All ({{ results.length }} matches)
			</BuilderButton>
			<div class="text-xs text-ink-gray-5">
				{{ replacedCount > 0 ? `${replacedCount} replacements made` : "" }}
			</div>
		</div>

		<div v-if="!query" class="mt-6 text-center">
			<!-- Empty State -->
			<div class="flex flex-col items-center justify-center py-8">
				<FeatherIcon name="search" class="mb-4 size-8 text-ink-gray-4" />
				<p class="mb-4 text-p-xs text-ink-gray-5">
					Find blocks by content, styles, attributes, or element type.
				</p>
			</div>
		</div>

		<div v-else-if="results.length > 0" class="max-h-64 overflow-y-auto">
			<!-- Search Results -->
			<div v-for="(result, index) in results" :key="result.blockId">
				<div
					class="mb-2 flex cursor-pointer items-center justify-between rounded px-3 py-2 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
					@mouseover.stop="canvasStore.activeCanvas?.setHoveredBlock(result.blockId)"
					@click="canvasStore.activeCanvas?.scrollBlockIntoView(result)">
					<div class="line-clamp-2 flex-1">
						{{ result.getBlockDescription() }}
						<div class="mt-1 text-xs text-ink-gray-5">
							{{ getMatchDetails(result) }}
						</div>
					</div>
					<BuilderButton
						v-if="searchMode === 'replace'"
						@click.stop="replaceInBlock(result, index)"
						variant="subtle"
						class="ml-3 px-2 py-1 text-xs"
						:disabled="!replaceQuery">
						Replace
					</BuilderButton>
				</div>
			</div>
		</div>

		<div v-else-if="query && results.length === 0" class="mt-6 text-center">
			<!-- No Results State -->
			<div class="flex flex-col items-center justify-center py-6">
				<FeatherIcon name="search" class="mb-3 size-6 text-ink-gray-4" />
				<h3 class="mb-1 text-sm font-medium text-ink-gray-6">No results found</h3>
				<p class="text-xs text-ink-gray-5">Try different keywords or adjust your filters</p>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { watchDebounced } from "@vueuse/core";
import { Badge, FeatherIcon } from "frappe-ui";
import { nextTick, onMounted, Ref, ref } from "vue";
import { toast } from "vue-sonner";
import BuilderButton from "./BuilderButton.vue";

const canvasStore = useCanvasStore();

const searchBlock = ref(null) as Ref<HTMLInputElement | null>;
const query = ref("");
const replaceQuery = ref("");
const searchMode = ref<"search" | "replace">("search");
const replacedCount = ref(0);
const results = ref([]) as Ref<Block[]>;

const propertyHandlers = [
	{
		key: "element",
		name: "Tag",
		matches: (block: Block, term: string) => block.getElement()?.toLowerCase().includes(term),
		replace: () => false,
	},
	{
		key: "content",
		name: "Content",
		matches: (block: Block, term: string) => block.getInnerHTML()?.toLowerCase().includes(term),
		replace: (block: Block, searchTerm: string, replaceTerm: string) => {
			const innerHTML = block.getInnerHTML();
			if (innerHTML) {
				const regex = new RegExp(escapeRegExp(searchTerm), "gi");
				if (regex.test(innerHTML)) {
					block.setInnerHTML(innerHTML.replace(regex, replaceTerm));
					return true;
				}
			}
			return false;
		},
	},
	{
		key: "styles",
		name: "Style",
		matches: (block: Block, term: string) => {
			const styles = { ...block.baseStyles, ...block.mobileStyles, ...block.tabletStyles };
			return Object.values(styles).some((val) => String(val).toLowerCase().includes(term));
		},
		replace: (block: Block, searchTerm: string, replaceTerm: string) => {
			let replaced = false;
			replaced = replaceInProperty(block.baseStyles, searchTerm, replaceTerm) || replaced;
			replaced = replaceInProperty(block.mobileStyles, searchTerm, replaceTerm) || replaced;
			replaced = replaceInProperty(block.tabletStyles, searchTerm, replaceTerm) || replaced;
			return replaced;
		},
	},
	{
		key: "attributes",
		name: "Attributes",
		matches: (block: Block, term: string) => {
			const attrs = { ...block.attributes, ...block.customAttributes };
			return Object.values(attrs).some((val) => String(val).toLowerCase().includes(term));
		},
		replace: (block: Block, searchTerm: string, replaceTerm: string) => {
			let replaced = false;
			replaced = replaceInProperty(block.attributes, searchTerm, replaceTerm) || replaced;
			replaced = replaceInProperty(block.customAttributes, searchTerm, replaceTerm) || replaced;
			return replaced;
		},
	},
	{
		key: "classes",
		name: "CSS Classes",
		matches: (block: Block, term: string) => {
			return block.classes?.some((c) => c.toLowerCase().includes(term));
		},
		replace: (block: Block, searchTerm: string, replaceTerm: string) => {
			if (!block.classes) return false;
			let hasReplacement = false;
			const regex = new RegExp(escapeRegExp(searchTerm), "gi");
			block.classes = block.classes.map((c) => {
				if (regex.test(c)) {
					hasReplacement = true;
					return c.replace(regex, replaceTerm);
				}
				return c;
			});
			return hasReplacement;
		},
	},
];

const filters = ref(
	propertyHandlers.map((h) => ({
		name: h.name,
		selected: false,
		key: h.key,
	})),
);

const setQuery = (value: string) => {
	query.value = value;
	replacedCount.value = 0;
};

const toggleSearchMode = () => {
	searchMode.value = searchMode.value === "search" ? "replace" : "search";
};

const toggleFilter = (filter: any) => {
	filter.selected = !filter.selected;
	performSearch();
};

const getMatchDetails = (block: Block) => {
	if (!query.value) return "";

	const lowerSearchTerm = query.value.toLowerCase();
	const details = propertyHandlers.filter((h) => h.matches(block, lowerSearchTerm)).map((h) => h.name);

	return details.length > 0 ? `Found in: ${details.join(", ")}` : "";
};

const replaceInProperty = (obj: any, searchTerm: string, replaceTerm: string): boolean => {
	let hasReplacement = false;

	if (typeof obj === "string") {
		return obj.toLowerCase().includes(searchTerm.toLowerCase());
	}

	if (typeof obj === "object" && obj !== null) {
		for (const key in obj) {
			if (typeof obj[key] === "string") {
				const regex = new RegExp(escapeRegExp(searchTerm), "gi");
				if (regex.test(obj[key])) {
					obj[key] = obj[key].replace(regex, replaceTerm);
					hasReplacement = true;
				}
			} else if (typeof obj[key] === "object") {
				hasReplacement = replaceInProperty(obj[key], searchTerm, replaceTerm) || hasReplacement;
			}
		}
	}

	return hasReplacement;
};

const escapeRegExp = (string: string) => {
	return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
};

const replaceInBlock = (block: Block, index: number) => {
	if (!replaceQuery.value || !query.value) return;

	let hasReplacement = false;
	const searchTerm = query.value;
	const replaceTerm = replaceQuery.value;
	const activeFilterKeys = filters.value.filter((f) => f.selected).map((f) => f.key);
	const replacers =
		activeFilterKeys.length > 0
			? propertyHandlers.filter((h) => activeFilterKeys.includes(h.key))
			: propertyHandlers;

	for (const replacer of replacers) {
		if (replacer.replace(block, searchTerm, replaceTerm)) {
			hasReplacement = true;
		}
	}

	if (hasReplacement) {
		replacedCount.value++;
		results.value.splice(index, 1);
		toast.success(`Replaced in ${block.getBlockDescription()}`);
	} else {
		toast.error("No replacements made");
	}
};

const replaceAll = () => {
	if (!replaceQuery.value || !query.value) return;

	let totalReplacements = 0;
	const blocksToReplace = [...results.value];

	blocksToReplace.forEach((block, index) => {
		const originalCount = replacedCount.value;
		replaceInBlock(block, 0); // Always use index 0 since we're working with a copy
		if (replacedCount.value > originalCount) {
			totalReplacements++;
		}
	});

	if (totalReplacements > 0) {
		toast.success(`Made ${totalReplacements} replacements across ${totalReplacements} blocks`);
		performSearch();
	} else {
		toast.error("No replacements made");
	}
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

const searchWithFilters = (searchTerm: string): Block[] => {
	const searchResults: Block[] = [];
	const limit = 50;
	const lowerSearchTerm = searchTerm.toLowerCase();

	const activeFilterKeys = filters.value.filter((f) => f.selected).map((f) => f.key);

	const searchers =
		activeFilterKeys.length > 0
			? propertyHandlers.filter((h) => activeFilterKeys.includes(h.key))
			: propertyHandlers;

	function searchInBlock(block: Block) {
		if (searchResults.length >= limit) return;
		const matches = searchers.some((s) => s.matches(block, lowerSearchTerm));
		if (matches) {
			searchResults.push(block);
		}
		block.children?.forEach((child) => searchInBlock(child));
	}

	const rootBlock = canvasStore.activeCanvas?.getRootBlock();
	if (rootBlock) {
		searchInBlock(rootBlock);
	}

	return searchResults;
};

onMounted(async () => {
	await nextTick();
	const input = searchBlock.value?.querySelector("input");
	input?.focus();
});

watchDebounced(query, performSearch, {
	debounce: 300,
});

watchDebounced(() => filters.value.map((f) => f.selected).join(","), performSearch, {
	debounce: 300,
});
</script>
