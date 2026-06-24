<template>
	<div class="relative w-full min-w-0">
		<Autocomplete
			ref="autocompleteRef"
			class="w-full"
			placeholder="Value"
			:modelValue="autocompleteValue"
			:getOptions="getOptions"
			:showInputAsOption="true"
			@update:modelValue="handleModelValueUpdate" />

		<div
			v-if="dynamicValue?.key"
			class="pointer-events-none absolute bottom-0 left-0 right-0 top-0 flex items-center gap-2 rounded bg-surface-violet-2 py-0.5 pl-2.5 pr-7 text-sm text-ink-violet-8">
			<span class="lucide-zap size-3 shrink-0" aria-hidden="true" />
			<MiddleTruncate :text="dynamicValue.key" />
		</div>

		<button
			v-if="dynamicValue?.key"
			class="absolute right-1 top-1 cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
			tabindex="-1"
			@click.stop="clearDynamicValue">
			<span class="lucide-x size-3.5" />
		</button>
	</div>
</template>

<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import MiddleTruncate from "@/components/MiddleTruncate.vue";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { getDataArray, getDefaultPropsList, getParentProps, getRepeaterScopedData } from "@/utils/helpers";
import { computed, ref, watch } from "vue";

type DynamicValue = {
	key: string;
	comesFrom: BlockDataKey["comesFrom"];
};

type Option = {
	label: string;
	value: string;
};

const props = defineProps<{
	modelValue: string;
	dynamicValue?: DynamicValue;
}>();

const emit = defineEmits<{
	(e: "update:modelValue", value: string): void;
	(e: "setDynamicValue", value: DynamicValue): void;
	(e: "clearDynamicValue"): void;
}>();

const pageStore = usePageStore();
const autocompleteRef = ref<InstanceType<typeof Autocomplete> | null>(null);

const currentBlock = computed(() => blockController.getFirstSelectedBlock());

const pageDataArray = computed(() => {
	if (!currentBlock.value) return [];
	return getDataArray(getRepeaterScopedData(currentBlock.value, pageStore.pageData));
});

const ownProps = computed(() => {
	if (!currentBlock.value) return [];
	return Object.keys(currentBlock.value.getBlockProps());
});

const parentProps = computed(() => {
	if (!currentBlock.value) return [];
	return Object.keys(getParentProps(currentBlock.value));
});

const defaultProps = computed(() => {
	if (!currentBlock.value) return [];
	return Object.keys(getDefaultPropsList(currentBlock.value, blockController));
});

const autocompleteValue = computed(() => {
	if (!props.dynamicValue?.key) return props.modelValue;
	return encodeDynamicValue(props.dynamicValue.key, props.dynamicValue.comesFrom);
});

const dynamicOptions = computed(() => {
	const options: Option[] = [];
	const addOption = (key: string, comesFrom: BlockDataKey["comesFrom"]) => {
		const value = encodeDynamicValue(key, comesFrom);
		if (!options.some((option) => option.value === value)) {
			options.push({ label: key, value });
		}
	};

	pageDataArray.value.forEach((key) => addOption(key, "dataScript"));
	[...ownProps.value, ...parentProps.value, ...defaultProps.value].forEach((key) => addOption(key, "props"));

	return options;
});

const getOptions = async (query: string) => {
	const normalizedQuery = query.trim().toLowerCase();
	return dynamicOptions.value.filter((option) => {
		return !normalizedQuery || option.label.toLowerCase().includes(normalizedQuery);
	});
};

const handleModelValueUpdate = (value: string | null) => {
	if (value == null) {
		clearDynamicValue();
		emit("update:modelValue", "");
		return;
	}

	const dynamicOption = dynamicOptions.value.find((option) => option.value === value);
	if (dynamicOption) {
		emit("setDynamicValue", decodeDynamicValue(dynamicOption.value));
		return;
	}

	clearDynamicValue();
	emit("update:modelValue", value);
};

const clearDynamicValue = () => {
	emit("clearDynamicValue");
	emit("update:modelValue", "");
};

const encodeDynamicValue = (key: string, comesFrom: BlockDataKey["comesFrom"]) => {
	return `${key}--${comesFrom}`;
};

const decodeDynamicValue = (value: string): DynamicValue => {
	const key = value.split("--").slice(0, -1).join("--");
	const comesFrom = value.split("--").slice(-1)[0] as BlockDataKey["comesFrom"];
	return { key, comesFrom };
};

watch(
	[pageDataArray, ownProps, parentProps, defaultProps],
	() => {
		autocompleteRef.value?.refreshOptions();
	},
	{ immediate: true },
);
</script>
