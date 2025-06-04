<template>
	<div class="relative w-full">
		<div
			class="absolute left-[-18px] top-1 z-50 hover:top-0"
			v-if="dynamicValueProperty && !dynamicValueAlreadySet">
			<Dropdown :options="dynamicKeyOptions" size="sm" placement="right">
				<template v-slot="{ open }">
					<div
						class="group flex cursor-pointer items-center gap-1 rounded-lg bg-purple-500 transition-all hover:size-fit hover:p-1.5">
						<span class="hidden text-xs text-ink-white group-hover:block">Set Dynamic Value</span>
						<FeatherIcon name="plus" class="size-3 text-ink-white" @click="open"></FeatherIcon>
					</div>
				</template>
			</Dropdown>
		</div>
		<FormControl
			:class="classes"
			:type="type"
			@change="triggerUpdate"
			@input="($event: Event) => emit('input', ($event.target as HTMLInputElement).value)"
			autocomplete="off"
			:autofocus="autofocus"
			v-bind="attrs"
			:modelValue="data">
			<template #prefix v-if="$slots.prefix">
				<slot name="prefix" />
			</template>
		</FormControl>
		<div
			class="absolute bottom-0 left-0 right-0 top-0 z-10 rounded bg-surface-violet-1 px-2 py-0.5 text-ink-violet-1"
			v-if="dynamicValueAlreadySet">
			{{ dynamicValue }}
		</div>
		<button
			class="absolute bottom-[3px] right-[1px] z-20 cursor-pointer p-1 text-ink-gray-4 hover:text-ink-gray-5"
			tabindex="-1"
			@click="clearValue"
			v-if="!['select', 'checkbox'].includes(type) && !hideClearButton"
			v-show="data || dynamicValueAlreadySet">
			<CrossIcon />
		</button>
	</div>
</template>
<script lang="ts" setup>
import Block from "@/block";
import CrossIcon from "@/components/Icons/Cross.vue";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";

import { useDebounceFn, useVModel } from "@vueuse/core";
import { Dropdown } from "frappe-ui";
import { computed, useAttrs } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue?: string | number | boolean | null;
		type?: string;
		hideClearButton?: boolean;
		autofocus?: boolean;
		dynamicValueProperty?: string;
	}>(),
	{
		type: "text",
		modelValue: "",
	},
);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);

defineOptions({
	inheritAttrs: false,
});

const classes = computed(() => {
	const _classes = [];
	if (!["select", "checkbox"].includes(props.type) && !props.hideClearButton && props.modelValue) {
		_classes.push("[&>div>input]:pr-7");
	}
	if (props.type === "checkbox") {
		_classes.push("[&>label]:text-ink-gray-7");
	}
	if (props.type === "select") {
		_classes.push(
			...[
				"[&>div>select]:text-ink-gray-8",
				"[&>label]:text-ink-gray-7",
				"[&>div>select]:border-outline-gray-1",
				"[&>div>select]:bg-surface-gray-2",
				"[&>div>select]:pr-7",
				"[&>div>select]:hover:border-outline-gray-2",
				"[&>div>select]:hover:bg-surface-gray-1",
				"focus:[&>div>select]:bg-surface-gray-1",
				"focus:[&>div>select]:border-outline-gray-3",
				"focus:[&>div>select]:ring-outline-gray-3",
			],
		);
	} else if (props.type === "textarea") {
		_classes.push([
			"[&>div>textarea]:border-outline-gray-1",
			"[&>label]:text-ink-gray-7",
			"[&>div>textarea]:!bg-surface-gray-2",
			"[&>div>textarea]:text-ink-gray-8",
			"[&>div>textarea]:focus:border-outline-gray-3",
			"[&>div>textarea]:focus:bg-surface-gray-1",
			"[&>div>textarea]:hover:!border-outline-gray-2",
			"[&>div>textarea]:hover:!bg-surface-gray-1",
			"focus:[&>div>textarea]:border-outline-gray-3",
			"focus:[&>div>textarea]:bg-surface-gray-1",
			"focus:[&>div>textarea]:ring-outline-gray-3",
		]);
	} else {
		_classes.push([
			"[&>label]:text-ink-gray-7",
			"[&>div>input]:border-outline-gray-1",
			"[&>div>input]:bg-surface-gray-2",
			"[&>div>input]:text-ink-gray-8",
			"text-sm",
			"[&>p]:text-p-xs",
			"[&>div>input]:hover:!border-outline-gray-2",
			"[&>div>input]:hover:!bg-surface-gray-1",
			"[&>div>input]:focus-visible:bg-surface-gray-1",
			"focus:[&>div>input]:border-outline-gray-3",
			"focus:[&>div>input]:bg-surface-gray-1",
			"focus:[&>div>input]:ring-outline-gray-3",
		]);
	}
	return _classes;
});

const attrs = useAttrs();

const clearValue = () => {
	if (dynamicValueAlreadySet.value) {
		clearDynamicValue();
	} else {
		data.value = "";
	}
};

const triggerUpdate = useDebounceFn(($event: Event) => {
	if (props.type === "checkbox") {
		emit("update:modelValue", ($event.target as HTMLInputElement).checked);
	} else {
		emit("update:modelValue", ($event.target as HTMLInputElement).value);
	}
}, 100);

const canvasStore = useCanvasStore();
let dynamicValueAlreadySet = computed(() => {
	const blocks = canvasStore.activeCanvas?.selectedBlocks;
	if (!blocks?.length) return;
	const dataKeyObj = blocks[0].dynamicValues.find((obj) => {
		if (obj.type == "style" && obj.property == props.dynamicValueProperty) {
			return true;
		}
	});
	if (dataKeyObj) {
		return true;
	} else {
		return false;
	}
});

const dynamicValue = computed(() => {
	const blocks = canvasStore.activeCanvas?.selectedBlocks;
	if (!blocks?.length) return;
	const dataKeyObj = blocks[0].dynamicValues.find((obj) => {
		if (obj.type == "style" && obj.property == props.dynamicValueProperty) {
			return true;
		}
	});
	if (dataKeyObj) {
		return dataKeyObj.key;
	} else {
		return "";
	}
});

const pageStore = usePageStore();
const dynamicKeyOptions = computed(() => {
	// pick keys from store.pageData
	return Object.keys(pageStore.pageData).map((key) => ({
		label: key,
		value: key,
		onClick: () => {
			// import blockController from "@/utils/blockController";
			import("@/utils/blockController").then((blockController) => {
				blockController.default?.getSelectedBlocks().forEach((block) => {
					block.dynamicValues.push({
						type: "style",
						key,
						property: props.dynamicValueProperty,
					});
				});
			});
		},
	}));
});

const clearDynamicValue = () => {
	const blocks = canvasStore.activeCanvas?.selectedBlocks as Block[];
	blocks[0].dynamicValues = blocks[0].dynamicValues.filter((obj) => {
		if (obj.type == "style" && obj.property == props.dynamicValueProperty) {
			return false;
		}
		return true;
	});
};
</script>
