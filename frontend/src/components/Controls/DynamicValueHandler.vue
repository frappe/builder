<template>
	<div class="flex min-h-36 flex-col justify-between gap-2">
		<div class="flex flex-col gap-2">
			<BuilderInput
				v-if="pageDataArray.length > 5"
				v-model="searchQuery"
				@input="(val: string) => (searchQuery = val)"
				type="text"
				placeholder="Search..." />
			<div class="max-h-[60vh] overflow-y-auto">
				<ul class="m-0 list-none p-0">
					<li
						v-if="
							selectedItem?.key &&
							!filteredItems.some(
								(i) => i.key === selectedItem!.key && i.comesFrom === selectedItem!.comesFrom,
							)
						">
						<div
							class="w-full cursor-pointer truncate rounded bg-surface-gray-3 p-2 text-left font-mono text-p-sm text-ink-gray-9"
							@click.stop="selectAndSetItem(selectedItem)">
							<MiddleTruncate :text="selectedItem.key" />
							<p class="truncate text-xs text-ink-gray-5" :class="{ italic: getValue(selectedItem) == null }">
								{{ getValue(selectedItem) == null ? "No Value Set" : getValue(selectedItem) }}
							</p>
						</div>
					</li>
					<li v-for="item in filteredItems" :key="item.key">
						<div
							class="w-full cursor-pointer truncate rounded p-2 text-left font-mono text-p-sm text-ink-gray-7 hover:bg-surface-gray-2"
							:class="{
								'bg-surface-gray-3 text-ink-gray-9':
									selectedItem?.key === item.key && selectedItem?.comesFrom === item.comesFrom,
							}"
							@click.stop="selectAndSetItem(item)">
							<MiddleTruncate :text="item.key" />
							<p class="truncate text-xs text-ink-gray-5" :class="{ italic: getValue(item) == null }">
								{{ getValue(item) == null ? "No Value Set" : getValue(item) }}
							</p>
						</div>
					</li>
					<li
						v-if="filteredItems.length === 0 && !selectedItem?.key"
						class="flex flex-col items-center justify-center p-10 text-center text-sm text-ink-gray-5">
						<div>
							No dynamic values found. Please add using
							<a
								href="#"
								@click="builderStore.showDataScriptDialog = 'page'"
								class="text-ink-gray-5 underline hover:text-ink-gray-7">
								Page Data Script
							</a>
							.
						</div>
					</li>
				</ul>
			</div>
		</div>
		<div
			class="flex items-center justify-end gap-2"
			v-if="filteredItems.length !== 0 && builderStore.leftPanelActiveTab !== 'Code'">
			<div class="flex gap-2">
				<Button variant="subtle" @click="builderStore.leftPanelActiveTab = 'Code'">Open Code Tab</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import {
	getDataArray,
	getDefaultPropsList,
	getParentProps,
	getPropValue,
	getRepeaterScopedData,
} from "@/utils/helpers";
import { computed, ref } from "vue";
import MiddleTruncate from "../MiddleTruncate.vue";
import useCanvasStore from "@/stores/canvasStore.js";
import componentController from "@/utils/componentController.js";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

type DynamicValueItem = {
	key: string;
	comesFrom: BlockDataKey["comesFrom"];
};

type DynamicValueFilterOptions = {
	excludePassedDownProps?: boolean;
	excludeOwnProps?: boolean;
};

const props = defineProps<{
	selectedValue?: DynamicValueItem;
	block?: Block;
	options?: DynamicValueFilterOptions;
}>();

const emit = defineEmits(["setDynamicValue"]);
const searchQuery = ref("");

const currentBlock = computed(() => {
	return props.block || blockController.getFirstSelectedBlock();
});

// Page Data Array maybe not be allowed in fragment mode
const pageDataArray = computed(() => {
	if (canvasStore.editingMode == "fragment") return [];
	return getDataArray(getRepeaterScopedData(currentBlock.value, pageStore.pageData));
});

const defaultProps = computed(() => {
	return getDefaultPropsList(currentBlock.value!);
});

const componentData = computed(() => {
	return componentController.getComponentDataPreview();
});

const componentDataArray = computed(() => {
	return getDataArray(getRepeaterScopedData(currentBlock.value, componentData.value, "componentData"));
});

const filteredBlockProps = computed(() => {
	let ownBlockProps: string[];
	if (props.options?.excludeOwnProps) {
		ownBlockProps = [];
	} else {
		ownBlockProps = Object.keys(currentBlock.value?.getBlockProps() || {});
	}
	let parentProps: string[];
	if (props.options?.excludePassedDownProps || !currentBlock.value) {
		parentProps = [];
	} else {
		parentProps = Object.keys(getParentProps(currentBlock.value));
	}
	const combinedProps = [...ownBlockProps, ...parentProps].reduce((acc, prop) => {
		if (!acc.find((p: string) => p === prop)) {
			acc.push(prop);
		}
		return acc;
	}, [] as string[]);
	return combinedProps;
});

const filteredItems = computed(() => {
	const pageDataArrayItems = pageDataArray.value.map((item) => ({ key: item, comesFrom: "dataScript" }));
	const componentDataArrayItems = componentDataArray.value.map((item) => ({
		key: item,
		comesFrom: "componentData",
	}));
	const propItems = filteredBlockProps.value.map((item) => ({ key: item, comesFrom: "props" }));
	const defaultPropsKeys = Object.keys(defaultProps.value || {}).map((item) => ({
		key: item,
		comesFrom: "props",
	}));
	const allItems = [
		...pageDataArrayItems,
		...componentDataArrayItems,
		...propItems,
		...defaultPropsKeys,
	] as DynamicValueItem[];
	if (!searchQuery.value) return allItems;
	const query = searchQuery.value.toLowerCase();
	return allItems.filter(
		(item) =>
			item.key.toLowerCase().includes(query) ||
			String(getDataScriptValue(item.key)).toLowerCase().includes(query) ||
			String(getPropValue(item.key, currentBlock.value, getDataScriptValue, defaultProps.value))
				.toLowerCase()
				.includes(query),
	);
});

const selectedItem = ref<DynamicValueItem | null>(props.selectedValue || null);

const getValue = (item: DynamicValueItem): any => {
	if (item.comesFrom == "props") {
		return getPropValue(item.key, currentBlock.value, getDataScriptValue, defaultProps.value);
	} else if (item.comesFrom == "componentData") {
		return getComponentDataValue(item.key);
	} else {
		return getDataScriptValue(item.key);
	}
};

const getDataScriptValue = (path: string): any => {
	const collectionObject = getRepeaterScopedData(currentBlock.value, pageStore.pageData);
	return path.split(".").reduce((obj: Record<string, any>, key: string) => obj?.[key], collectionObject);
};

const getComponentDataValue = (path: string): any => {
	const collectionObject = getRepeaterScopedData(currentBlock.value, componentData.value, "componentData");
	return path.split(".").reduce((obj: Record<string, any>, key: string) => obj?.[key], collectionObject);
};

function selectAndSetItem(item: DynamicValueItem) {
	selectedItem.value = item;
	emit("setDynamicValue", item);
	selectedItem.value = null;
}
</script>
