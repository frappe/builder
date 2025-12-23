<template>
	<component
		:is="getComponentName(block)"
		:selected="isSelected"
		:data-block-id="block.blockId"
		:data-block-uid="uid"
		:data-breakpoint="breakpoint"
		:draggable="draggable"
		:class="classes"
		v-bind="attributes"
		:readonly="readonly"
		:style="styles"
		ref="component">
		<BuilderBlock
			:data="data"
			:block-data="cumulativeBlockData"
			:defaultProps="defaultProps"
			:block="child"
			:breakpoint="breakpoint"
			:preview="preview"
			:readonly="readonly"
			:isChildOfComponent="block.isExtendedFromComponent() || isChildOfComponent"
			:key="child.blockId"
			v-for="child in block.getChildren().filter((child) => child.isVisible(breakpoint))" />
	</component>
	<teleport to="#overlay" v-if="canvasProps?.overlayElement && !preview && Boolean(canvasProps)">
		<!-- prettier-ignore -->
		<BlockEditor
			ref="editor"
			v-show="!isEditable"
			v-if="loadEditor"
			:block="block"
			:breakpoint="breakpoint"
			:editable="isEditable"
			:isSelected="isSelected"
			:readonly="readonly"
			:target="(target as HTMLElement)" />
	</teleport>
</template>
<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { setFont } from "@/utils/fontManager";
import { getDataForKey, getPropValue, saferExecuteBlockClientScript } from "@/utils/helpers";
import { useDraggableBlock } from "@/utils/useDraggableBlock";
import { computed, inject, nextTick, onMounted, reactive, ref, useAttrs, watch, watchEffect } from "vue";
import BlockEditor from "./BlockEditor.vue";
import BlockHTML from "./BlockHTML.vue";
import DataLoaderBlock from "./DataLoaderBlock.vue";
import TextBlock from "./TextBlock.vue";
import { builderSettings } from "@/data/builderSettings";
import fetchBlockData from "@/data/blockData";
import usePageStore from "@/stores/pageStore";
import { toast } from "vue-sonner";
import useBlockDataStore from "@/stores/blockDataStore";

const canvasStore = useCanvasStore();
const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
const attrs = useAttrs();
const editor = ref<InstanceType<typeof BlockEditor> | null>(null);
const pageStore = usePageStore();
const blockDataStore = useBlockDataStore();

const props = withDefaults(
	defineProps<{
		block: Block;
		isChildOfComponent?: boolean;
		breakpoint?: string;
		preview?: boolean;
		readonly?: boolean;
		data?: Record<string, any> | null;
		blockData?: Record<string, any> | null;
		defaultProps?: Record<string, any> | null;
	}>(),
	{
		isChildOfComponent: false,
		breakpoint: "desktop",
		preview: false,
		readonly: false,
		data: null,
		blockData: null,
		defaultProps: null,
	},
);

defineOptions({
	inheritAttrs: false,
});

const draggable = computed(() => {
	// TODO: enable this
	return !props.block.isRoot() && !props.preview && false;
});

const isHovered = ref(false);
const isSelected = ref(false);
const ownBlockData = ref<Record<string, any>>({});

const uid = `builder-block-${props.block.blockId}-${Math.random().toString(36).substr(2, 9)}`;

const getComponentName = (block: Block) => {
	if (block.isRepeater()) {
		return DataLoaderBlock;
	}
	if (block.isText() || block.isLink() || block.isButton()) {
		return TextBlock;
	} else if (block.isHTML()) {
		return BlockHTML;
	} else {
		return block.getTag();
	}
};

const classes = computed(() => {
	return [
		attrs.class,
		"__builder_component__",
		"outline-none",
		"select-none",
		...props.block.getClasses(),
		hiddenDueToVisibilityCondition.value ? "opacity-10" : "",
	];
});

const hasBlockProps = computed(() => {
	return props.defaultProps || Object.keys(props.block.getBlockProps()).length > 0;
});

const cumulativeBlockData = computed(() => {
	return {
		...props.blockData,
		...ownBlockData.value,
	};
});

const getDataScriptValue = (path: string): any => {
	return getDataForKey(props.data || {}, path);
};
const getBlockDataScriptValue = (path: string): any => {
	return getDataForKey(cumulativeBlockData.value, path);
};

const attributes = computed(() => {
	const attribs = { ...props.block.getAttributes(), ...attrs } as { [key: string]: any };
	if (
		props.block.isText() ||
		props.block.isHTML() ||
		props.block.isLink() ||
		props.block.isButton() ||
		props.block.isRepeater()
	) {
		attribs.block = props.block;
		attribs.preview = props.preview;
		attribs.breakpoint = props.breakpoint;
		attribs.data = props.data;
		attribs.blockData = cumulativeBlockData.value;
		attribs.defaultProps = props.defaultProps;
	}

	if (props.data || hasBlockProps.value) {
		if (props.block.getDataKey("type") === "attribute") {
			let value;
			if (props.block.getDataKey("comesFrom") === "props") {
				value = getPropValue(
					props.block.getDataKey("key") as string,
					props.block,
					getDataScriptValue,
					getBlockDataScriptValue,
					props.defaultProps,
				);
			} else if (props.block.getDataKey("comesFrom") === "blockDataScript") {
				value = getBlockDataScriptValue(props.block.getDataKey("key") as string);
			} else {
				value = getDataScriptValue(props.block.getDataKey("key") as string);
			}
			attribs[props.block.getDataKey("property") as string] =
				value ?? attribs[props.block.getDataKey("property") as string];
		}
		props.block.dynamicValues
			?.filter((dataKeyObj: BlockDataKey) => {
				return dataKeyObj.type === "attribute";
			})
			?.forEach((dataKeyObj: BlockDataKey) => {
				const property = dataKeyObj.property as string;
				let value;
				if (dataKeyObj.comesFrom === "props") {
					value = getPropValue(
						dataKeyObj.key as string,
						props.block,
						getDataScriptValue,
						getBlockDataScriptValue,
						props.defaultProps,
					);
				} else if (dataKeyObj.comesFrom === "blockDataScript") {
					value = getBlockDataScriptValue(dataKeyObj.key as string);
				} else {
					value = getDataScriptValue(dataKeyObj.key as string);
				}
				attribs[property] = value ?? attribs[property];
			});
	}

	if (props.block.isInput()) {
		attribs.readonly = true;
	}
	return attribs;
});

const canvasProps = !props.preview ? (inject("canvasProps") as CanvasProps) : null;

const target = computed(() => {
	if (!component.value) return null;
	if (component.value instanceof HTMLElement || component.value instanceof SVGElement) {
		return component.value;
	} else {
		return component.value.component;
	}
});

const styles = computed(() => {
	let dynamicStyles = {} as { [key: string]: string };
	if (props.data || hasBlockProps.value) {
		if (props.block.getDataKey("type") === "style") {
			let value;
			if (props.block.getDataKey("comesFrom") === "props") {
				value = getPropValue(
					props.block.getDataKey("key") as string,
					props.block,
					getDataScriptValue,
					getBlockDataScriptValue,
					props.defaultProps,
				);
			} else if (props.block.getDataKey("comesFrom") === "blockDataScript") {
				value = getBlockDataScriptValue(props.block.getDataKey("key") as string);
			} else {
				value = getDataForKey(props.data as Object, props.block.getDataKey("key") as string);
			}
			dynamicStyles = {
				[props.block.getDataKey("property") as string]: value,
			};
		}
		props.block.dynamicValues
			?.filter((dataKeyObj: BlockDataKey) => {
				return dataKeyObj.type === "style";
			})
			?.forEach((dataKeyObj: BlockDataKey) => {
				const property = dataKeyObj.property as string;
				let value;
				if (dataKeyObj.comesFrom === "props") {
					value = getPropValue(
						dataKeyObj.key as string,
						props.block,
						getDataScriptValue,
						getBlockDataScriptValue,
						props.defaultProps,
					);
				} else if (dataKeyObj.comesFrom === "blockDataScript") {
					value = getBlockDataScriptValue(dataKeyObj.key as string);
				} else {
					value = getDataForKey(props.data as Object, dataKeyObj.key as string);
				}
				dynamicStyles[property] = value ?? dynamicStyles[property];
			});
	}

	const styleMap = {
		...props.block.getStyles(props.breakpoint),
		...props.block.getEditorStyles(),
		...dynamicStyles,
	} as BlockStyleMap;

	if (props.block.activeState) {
		const [state, property] = props.block.activeState.split(":");

		if (canvasStore.activeCanvas?.activeBreakpoint === props.breakpoint) {
			const stateStyles = props.block.getStateStyles(state, props.breakpoint);
			if (stateStyles) {
				Object.keys(stateStyles).forEach((key) => {
					if (key === property) {
						styleMap[key] = stateStyles[key];
					}
				});
			}
		}
	}

	// escape space in font family
	if (styleMap.fontFamily && typeof styleMap.fontFamily === "string") {
		styleMap.fontFamily = (styleMap.fontFamily as string).replace(/ /g, "\\ ");
	}

	Object.keys(styleMap).forEach((key) => {
		if (key.startsWith("hover:")) {
			// state style preview on hover
			// if (!isHovered.value) {
			// 	delete styleMap[key];
			// } else {
			// 	styleMap[key.replace("hover:", "")] = styleMap[key];
			// 	delete styleMap[key];
			// }
			delete styleMap[key];
		}
	});

	return styleMap;
});

const loadEditor = computed(() => {
	return (
		target.value &&
		props.block.getStyle("display") !== "none" &&
		((isSelected.value && props.breakpoint === canvasStore.activeCanvas?.activeBreakpoint) ||
			(isHovered.value && canvasStore.activeCanvas?.hoveredBreakpoint === props.breakpoint)) &&
		!canvasProps?.scaling &&
		!canvasProps?.panning
	);
});

const emit = defineEmits(["mounted"]);

watchEffect(() => {
	setFont(props.block.getStyle("fontFamily") as string, props.block.getStyle("fontWeight") as string);
});

onMounted(async () => {
	await nextTick();
	emit("mounted", target.value);

	if (draggable.value) {
		useDraggableBlock(
			props.block,
			component.value as HTMLElement,
			reactive({ ghostScale: canvasProps?.scale || 1 }),
		);
	}
});

const allResolvedProps = computed(() => {
	return {
		...props.defaultProps,
		...Object.fromEntries(
			Object.entries(props.block.getBlockProps()).map(([key, prop]) => {
				return [
					key,
					getPropValue(
						key,
						props.block,
						getDataScriptValue,
						(path: string) => ({ ...props.blockData }[path]), // block props can not refer to own block data items
						props.defaultProps,
					),
				];
			}),
		),
	};
});

watch(
	[
		component,
		allResolvedProps,
		() => props.block.getBlockClientScript(),
		() => Boolean(builderSettings.doc?.execute_block_scripts_in_editor),
		() => pageStore.settingPage,
	],
	() => {
		if (pageStore.settingPage) return;
		if (builderSettings.doc?.execute_block_scripts_in_editor) {
			saferExecuteBlockClientScript(uid, props.block.getBlockClientScript(), allResolvedProps.value);
		}
	},
	{ deep: true },
);

watch(
	() => props.blockData,
	() => {
		blockDataStore.setBlockData(props.block.blockId, props.blockData || {}, "passedDown");
	},
);

watch(
	[component, allResolvedProps, () => props.block.getBlockDataScript(), () => pageStore.settingPage],
	() => {
		if (pageStore.settingPage) return;
		if (props.block.getBlockDataScript().trim() === "") {
			ownBlockData.value = {};
			blockDataStore.setBlockData(props.block.blockId, {}, "own");
			return;
		}
		fetchBlockData
			.fetch({
				block_id: props.block.blockId,
				block_data_script: props.block.getBlockDataScript(),
				props: JSON.stringify(allResolvedProps.value),
			})
			.then((res: any) => {
				ownBlockData.value = res || {};
				blockDataStore.setBlockData(props.block.blockId, res || {}, "own");
			})
			.catch((e: { exc: string | null }) => {
				const error_message = e.exc?.split("\n").slice(-2)[0];
				toast.error("There was an error while fetching page data", {
					description: error_message,
				});
			});
	},
	{ deep: true },
);

const isEditable = computed(() => {
	// to ensure it is right block and not on different breakpoint
	return (
		canvasStore.editableBlock === props.block &&
		canvasStore.activeCanvas?.activeBreakpoint === props.breakpoint
	);
});

const hiddenDueToVisibilityCondition = computed(() => {
	return props.block.getVisibilityCondition()
		? !Boolean(getDataForKey(props.data || {}, props.block.getVisibilityCondition() as string))
		: false;
});

if (!props.preview) {
	watch(
		() => canvasStore.activeCanvas?.hoveredBlock,
		(newValue, oldValue) => {
			if (newValue === props.block.blockId) {
				isHovered.value = true;
			} else if (oldValue === props.block.blockId) {
				isHovered.value = false;
			}
		},
	);
	watch(
		() => canvasStore.activeCanvas?.selectedBlockIds,
		() => {
			if (canvasStore.activeCanvas?.isSelected(props.block)) {
				isSelected.value = true;
			} else {
				isSelected.value = false;
			}
		},
		{
			deep: true,
			immediate: true,
		},
	);
}

// Note: All the block event listeners are delegated to parent for better scalability
</script>
