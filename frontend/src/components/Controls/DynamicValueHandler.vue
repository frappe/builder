<template>
	<div class="flex min-h-36 flex-col justify-between gap-2">
		<div class="flex flex-col gap-2">
			<BuilderInput
				v-if="pageDataArray.length + blockDataArray.length > 5"
				v-model="searchQuery"
				@input="(val: string) => (searchQuery = val)"
				type="text"
				placeholder="Search..." />
			<div class="max-h-[60vh] overflow-y-auto">
				<ul class="m-0 list-none p-0">
					<li
						v-if="selectedItem?.key && !filteredItems.some(i => i.key === selectedItem!.key && i.comesFrom === selectedItem!.comesFrom)">
						<div
							class="w-full cursor-pointer truncate rounded bg-surface-gray-3 p-2 text-left font-mono text-p-sm text-ink-gray-9"
							@click.stop="selectAndSetItem(selectedItem)">
							{{ selectedItem.key }}
							<p class="truncate text-xs text-ink-gray-5" :class="{ italic: getValue(selectedItem) == null }">
								{{ getValue(selectedItem) == null ? "No Value Set" : getValue(selectedItem) }}
							</p>
						</div>
					</li>
					<li v-for="(item, index) in filteredItems" :key="index">
						<div
							class="w-full cursor-pointer truncate rounded p-2 text-left font-mono text-p-sm text-ink-gray-7 hover:bg-surface-gray-2"
							:class="{
								'bg-surface-gray-3 text-ink-gray-9':
									selectedItem?.key === item.key && selectedItem?.comesFrom === item.comesFrom,
							}"
							@click.stop="selectAndSetItem(item)">
							{{ item.key }}
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
								@click="builderStore.showDataScriptDialog = true"
								class="text-ink-gray-5 underline hover:text-ink-gray-7">
								Data Script,
							</a>
							or block props.
						</div>
					</li>
				</ul>
			</div>
		</div>
		<div class="flex items-center justify-end gap-2" v-if="filteredItems.length !== 0">
			<div class="flex gap-2">
				<Button variant="subtle" @click="builderStore.showDataScriptDialog = true">Edit Code</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import Block from "@/block";
import useBlockDataStore from "@/stores/blockDataStore";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { getDataArray, getParentProps, getPropValue, getStandardPropValue } from "@/utils/helpers";
import { computed, ref } from "vue";

const pageStore = usePageStore();
const builderStore = useBuilderStore();
const blockDataStore = useBlockDataStore();

type DynamicValueItem = {
	key: string;
	comesFrom: BlockDataKey["comesFrom"];
};

type DynamicValueFilterOptions = {
	excludePassedDownProps?: boolean;
	excludePassedDownBlockData?: boolean;
	excludeOwnProps?: boolean;
	excludeOwnBlockData?: boolean;
};

const props = defineProps<{
	selectedValue?: DynamicValueItem;
	block?: Block;
	options?: DynamicValueFilterOptions;
}>();

const emit = defineEmits(["setDynamicValue"]);
const searchQuery = ref("");

const pageDataArray = computed(() => {
	const currentBlock = props.block || blockController.getFirstSelectedBlock();
	return getDataArray(blockDataStore.getPageData(currentBlock?.blockId) || pageStore.pageData);
});

const blockDataArray = computed(() => {
	if (props.options?.excludeOwnBlockData && props.options.excludePassedDownBlockData) return [];
	const currentBlock = props.block || blockController.getFirstSelectedBlock();
	let filter: "all" | "own" | "passedDown" = "all";
	if (props.options?.excludeOwnBlockData) {
		filter = "passedDown";
	} else if (props.options?.excludePassedDownBlockData) {
		filter = "own";
	}
	if (currentBlock) {
		return getDataArray(blockDataStore.getBlockData(currentBlock.blockId, filter) || {});
	}
	return [];
});

const defaultProps = computed(() => {
	const currentBlock = props.block || blockController.getFirstSelectedBlock();
	const isCurrentBlockInRepeater = currentBlock?.isInsideRepeater();
	const repeaterRoot = isCurrentBlockInRepeater ? currentBlock?.getRepeaterParent() : null;
	if (repeaterRoot) {
		const key = repeaterRoot.getDataKey("key");
		const comesFrom = repeaterRoot.getDataKey("comesFrom");
		if (key && comesFrom === "props") {
			const componentRoot = blockController.getComponentRootBlock(repeaterRoot);
			const parsedValue = getStandardPropValue(key, componentRoot)?.value;
			if (!parsedValue) return {};
			if (Array.isArray(parsedValue)) {
				return {
					item: {
						value: parsedValue[0],
						isStandard: false,
						type: "static",
					},
				};
			} else if (typeof parsedValue === "object") {
				return {
					key: {
						value: Object.keys(parsedValue)[0],
						isStandard: false,
						type: "static",
					},
					value: {
						value: parsedValue[Object.keys(parsedValue)[0]],
						isStandard: false,
						type: "static",
					},
				};
			}
		}
	}
	return {};
});

const filteredBlockProps = computed(() => {
	let ownBlockProps: string[];
	if (props.options?.excludeOwnProps) {
		ownBlockProps = [];
	} else {
		ownBlockProps = Object.keys(
			props.block
				? props.block.getBlockProps()
				: blockController.getFirstSelectedBlock()?.getBlockProps() || {},
		);
	}
	let parentProps: string[];
	if (props.options?.excludePassedDownProps) {
		parentProps = [];
	} else {
		const currentBlock = props.block || blockController.getFirstSelectedBlock();
		if (currentBlock) {
			parentProps = Object.keys(getParentProps(currentBlock, {}));
		} else {
			parentProps = [];
		}
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
	const blockDataArrayItems = blockDataArray.value.map((item) => ({
		key: item,
		comesFrom: "blockDataScript",
	}));
	const propItems = filteredBlockProps.value.map((item) => ({ key: item, comesFrom: "props" }));
	const defaultPropsKeys = Object.keys(defaultProps.value || {}).map((item) => ({
		key: item,
		comesFrom: "props",
	}));
	const allItems = [
		...pageDataArrayItems,
		...blockDataArrayItems,
		...propItems,
		...defaultPropsKeys,
	] as DynamicValueItem[];
	if (!searchQuery.value) return allItems;
	const query = searchQuery.value.toLowerCase();
	return allItems.filter(
		(item) =>
			item.key.toLowerCase().includes(query) ||
			String(getDataScriptValue(item.key)).toLowerCase().includes(query) ||
			String(
				getPropValue(
					item.key,
					props.block || blockController.getFirstSelectedBlock(),
					getDataScriptValue,
					getBlockDataScriptValue,
					defaultProps.value,
				),
			)
				.toLowerCase()
				.includes(query),
	);
});

const selectedItem = ref<DynamicValueItem | null>(props.selectedValue || null);

const getValue = (item: DynamicValueItem): any => {
	if (item.comesFrom == "props") {
		return getPropValue(
			item.key,
			props.block || blockController.getFirstSelectedBlock(),
			getDataScriptValue,
			getBlockDataScriptValue,
			defaultProps.value,
		);
	} else if (item.comesFrom == "blockDataScript") {
		return getBlockDataScriptValue(item.key);
	} else {
		return getDataScriptValue(item.key);
	}
};

const getDataScriptValue = (path: string): any => {
	let collectionObject = props.block
		? blockDataStore.getPageData(props.block.blockId) || {}
		: blockDataStore.getPageData(blockController.getFirstSelectedBlock()?.blockId || "") || {};
	collectionObject = collectionObject || pageStore.pageData || {};

	return path.split(".").reduce((obj: Record<string, any>, key: string) => obj?.[key], collectionObject);
};

const getBlockDataScriptValue = (path: string): any => {
	let collectionObject = props.block
		? blockDataStore.getBlockData(props.block.blockId) || {}
		: blockDataStore.getBlockData(blockController.getFirstSelectedBlock()?.blockId || "") || {};

	return path.split(".").reduce((obj: Record<string, any>, key: string) => obj?.[key], collectionObject);
};
function selectAndSetItem(item: DynamicValueItem) {
	selectedItem.value = item;
	emit("setDynamicValue", item);
	selectedItem.value = null;
}
</script>
