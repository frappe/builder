<template>
	<div class="flex min-h-36 flex-col justify-between gap-2">
		<div class="flex flex-col gap-2">
			<BuilderInput
				v-if="dataArray.length > 5"
				v-model="searchQuery"
				@input="(val: string) => (searchQuery = val)"
				type="text"
				placeholder="Search..." />
			<div class="max-h-[60vh] overflow-y-auto">
				<ul class="m-0 list-none p-0">
					<li v-if="selectedKey && !filteredItems.includes(selectedKey)">
						<div
							class="w-full truncate rounded bg-surface-gray-3 p-2 text-left font-mono text-p-sm text-ink-gray-9"
							@click.stop="selectKey(selectedKey)">
							{{ selectedKey }}
							<p class="truncate text-xs text-ink-gray-5" :class="{ italic: getValue(selectedKey) == null }">
								{{ getValue(selectedKey) == null ? "No Value Set" : getValue(selectedKey) }}
							</p>
						</div>
					</li>
					<li v-for="(item, index) in filteredItems" :key="index">
						<div
							class="w-full truncate rounded p-2 text-left font-mono text-p-sm text-ink-gray-7 hover:bg-surface-gray-2"
							:class="{ 'bg-surface-gray-3 text-ink-gray-9': selectedKey === item }"
							@click.stop="selectKey(item)">
							{{ item }}
							<p class="truncate text-xs text-ink-gray-5" :class="{ italic: getValue(item) == null }">
								{{ getValue(item) == null ? "No Value Set" : getValue(item) }}
							</p>
						</div>
					</li>
					<li
						v-if="filteredItems.length === 0 && !selectedKey"
						class="flex flex-col items-center justify-center p-10 text-center text-sm text-ink-gray-5">
						<div>
							No dynamic values found. Please add using
							<a
								href="#"
								@click="builderStore.showDataScriptDialog = true"
								class="text-ink-gray-5 underline hover:text-ink-gray-7">
								Data Script
							</a>
						</div>
					</li>
				</ul>
			</div>
		</div>
		<div class="flex items-center justify-end gap-2" v-if="dataArray.length !== 0">
			<div class="flex gap-2">
				<Button variant="subtle" @click="builderStore.showDataScriptDialog = true">Edit Code</Button>
				<Button variant="solid" @click="saveSelection" :disabled="!selectedKey">Set</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { computed, ref } from "vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();

const props = defineProps<{
	selectedValue?: string;
	block?: Block;
}>();

const emit = defineEmits(["setDynamicValue"]);
const searchQuery = ref("");

const dataArray = computed(() => {
	const result: string[] = [];
	if (
		blockController.getFirstSelectedBlock()?.isInsideRepeater() &&
		blockController.getFirstSelectedBlock()?.getRepeaterParent()
	) {
		const repeaterBlock = blockController.getFirstSelectedBlock().getRepeaterParent();
		const collectionKey = repeaterBlock?.getDataKey("key") || "";
		if (
			collectionKey &&
			typeof pageStore.pageData[collectionKey] !== "undefined" &&
			Array.isArray(pageStore.pageData[collectionKey]) &&
			pageStore.pageData[collectionKey].length > 0
		) {
			const firstItem = pageStore.pageData[collectionKey][0];
			if (firstItem && typeof firstItem === "object" && firstItem !== null) {
				Object.entries(firstItem as Record<string, unknown>).forEach(([key, value]) => {
					if (!Array.isArray(value) && (typeof value !== "object" || value === null)) {
						result.push(key);
					}
				});
				return result;
			}
		}
	}

	function processObject(obj: Record<string, any>, prefix = "") {
		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (typeof value === "object" && value !== null && !Array.isArray(value)) {
				processObject(value, path);
			} else if (["string", "number", "boolean"].includes(typeof value)) {
				result.push(path);
			}
		});
	}

	processObject(pageStore.pageData);
	return result;
});

const getValue = (path: string): any => {
	if (
		blockController.getFirstSelectedBlock()?.isInsideRepeater() &&
		blockController.getFirstSelectedBlock()?.getRepeaterParent()
	) {
		const repeaterBlock = blockController.getFirstSelectedBlock().getRepeaterParent();
		const collectionKey = repeaterBlock?.getDataKey("key") || "";
		const collection = pageStore.pageData[collectionKey];

		if (collection && Array.isArray(collection) && collection.length > 0) {
			const firstItem = collection[0];
			if (firstItem && typeof firstItem === "object" && firstItem !== null) {
				return (firstItem as Record<string, unknown>)[path];
			}
		}
	}
	return path.split(".").reduce((obj: Record<string, any>, key: string) => obj?.[key], pageStore.pageData);
};

const filteredItems = computed(() => {
	if (!searchQuery.value) return dataArray.value;
	const query = searchQuery.value.toLowerCase();
	return dataArray.value.filter(
		(item) => item.toLowerCase().includes(query) || String(getValue(item)).toLowerCase().includes(query),
	);
});

const selectedKey = ref<string | null>(props.selectedValue || null);

function selectKey(key: string) {
	selectedKey.value = key;
}

function saveSelection() {
	if (selectedKey.value) {
		emit("setDynamicValue", selectedKey.value);
		selectedKey.value = null;
	}
}
</script>
