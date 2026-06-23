<template>
	<component
		:is="getComponentName(block)"
		:selected="isSelected"
		:data-block-id="block.blockId"
		:data-block-uid="uidToUse"
		:data-breakpoint="breakpoint"
		:draggable="draggable"
		:class="classes"
		v-bind="attributes"
		:readonly="readonly"
		:style="styles"
		ref="component">
		<BuilderBlock
			:data="data"
			:componentData="resolvedComponentData"
			:defaultProps="defaultProps"
			:block="child"
			:breakpoint="breakpoint"
			:preview="preview"
			:readonly="readonly"
			:isChildOfComponent="block.isExtendedFromComponent() || isChildOfComponent"
			:key="child.blockId"
			:repeater-index="repeaterIndex"
			:parent-block-uid="uidToUse"
			v-for="child in block.getChildren().filter((child) => child.isVisible(breakpoint))" />
	</component>
	<teleport
		:to="canvasProps?.overlayElement"
		v-if="canvasProps?.overlayElement && !preview && Boolean(canvasProps)">
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
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { setFont } from "@/utils/fontManager";
import { extractComponentId, getDataForKey, getParentProps, getPropValue } from "@/utils/helpers";
import { useDraggableBlock } from "@/utils/useDraggableBlock";
import {
	computed,
	inject,
	nextTick,
	onMounted,
	onUnmounted,
	reactive,
	ref,
	useAttrs,
	watch,
	watchEffect,
} from "vue";
import BlockEditor from "./BlockEditor.vue";
import BlockHTML from "./BlockHTML.vue";
import DataLoaderBlock from "./DataLoaderBlock.vue";
import TextBlock from "./TextBlock.vue";
import componentController from "@/utils/componentController.js";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const componentStore = useComponentStore();
const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
const attrs = useAttrs();
const isMounted = ref(false);

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		block: Block;
		isChildOfComponent?: boolean;
		breakpoint?: string;
		preview?: boolean;
		readonly?: boolean;
		data?: Record<string, any> | null;
		componentData?: Record<string, any> | null;
		defaultProps?: Record<string, any> | null;
		repeaterIndex?: string | number | null;
		parentBlockUid?: string | null;
	}>(),
	{
		isChildOfComponent: false,
		breakpoint: "desktop",
		preview: false,
		readonly: false,
		data: null,
		componentData: null,
		defaultProps: null,
		repeaterIndex: null,
		parentBlockUid: null,
	},
);

const resolvedComponentData = computed(() => {
	if (canvasStore.editingMode == "fragment" && !props.block.getParentBlock()) {
		return componentController.getComponentDataPreview();
	}
	const componentId = extractComponentId(props.block);
	if (componentId) {
		return componentStore.getComponentInstanceData(componentId, uidToUse);
	} else {
		return props.componentData;
	}
});

defineOptions({
	inheritAttrs: false,
});

const draggable = computed(() => {
	// TODO: enable this
	return !props.block.isRoot() && !props.preview && false;
});

const isHovered = ref(false);
const isSelected = ref(false);

// For repeater items the same Block object is rendered multiple times,
// so we need a unique identifier per rendered instance (used by client scripts)
const uidToUse = !!props.repeaterIndex
	? `builder-block-${props.block.blockId}-${props.repeaterIndex}`
	: props.block.blockId;

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

const getDataScriptValue = (path: string): any => {
	return getDataForKey(props.data || {}, path);
};

const getComponentDataValue = (path: string): any => {
	return getDataForKey(props.componentData || {}, path);
};

const attributes = computed(() => {
	const RESTRICTED_ATTRIBS = ["data-block-id", "data-block-uid", "data-breakpoint"];
	let additionalAttributes: Record<string, any> = {};

	if (builderSettings.doc?.execute_block_scripts_in_editor !== "Don't Execute") {
		additionalAttributes = props.block.getCustomAttributes();
	}

	Object.keys(additionalAttributes).forEach((key) => {
		const trimmedKey = key.trim();
		if (RESTRICTED_ATTRIBS.includes(trimmedKey) || trimmedKey === "") {
			delete additionalAttributes[key];
		} else if (trimmedKey !== key) {
			additionalAttributes[trimmedKey] = additionalAttributes[key];
			delete additionalAttributes[key];
		}
	});

	const attribs = { ...additionalAttributes, ...props.block.getAttributes(), ...attrs } as {
		[key: string]: any;
	};

	if (props.block.isImage() && !props.preview) {
		if (builderStore.canvasDarkMode && attribs.darkSrc) {
			attribs.src = attribs.darkSrc;
		}
		if (attribs.darkSrc && !attribs.src) {
			attribs.src = attribs.darkSrc;
		}
		delete attribs.darkSrc;
	}

	if (
		props.block.isText() ||
		props.block.isHTML() ||
		props.block.isLink() ||
		props.block.isButton() ||
		props.block.isRepeater()
	) {
		attribs.block = props.block;
		attribs.repeaterIndex = props.repeaterIndex;
		attribs.preview = props.preview;
		attribs.breakpoint = props.breakpoint;
		attribs.data = props.data;
		attribs.componentData = props.componentData;
		attribs.defaultProps = props.defaultProps;
	}

	if (
		props.data ||
		hasBlockProps.value ||
		(props.componentData && Object.keys(props.componentData).length > 0)
	) {
		if (props.block.getDataKey("type") === "attribute") {
			let value;
			if (props.block.getDataKey("comesFrom") === "props") {
				value = getPropValue(
					props.block.getDataKey("key") as string,
					props.block,
					getDataScriptValue,
					props.defaultProps,
					getComponentDataValue,
				);
			} else {
				value = getDataScriptValue(props.block.getDataKey("key") as string);
			}
			attribs[props.block.getDataKey("property") as string] =
				value ?? attribs[props.block.getDataKey("property") as string];
		}
		props.block
			.getDynamicValues()
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
						props.defaultProps,
						getComponentDataValue,
					);
				} else if (dataKeyObj.comesFrom === "componentData") {
					value = getComponentDataValue(dataKeyObj.key as string);
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
	if (
		props.data ||
		hasBlockProps.value ||
		(props.componentData && Object.keys(props.componentData).length > 0)
	) {
		if (props.block.getDataKey("type") === "style") {
			let value;
			if (props.block.getDataKey("comesFrom") === "props") {
				value = getPropValue(
					props.block.getDataKey("key") as string,
					props.block,
					getDataScriptValue,
					props.defaultProps,
					getComponentDataValue,
				);
			} else {
				value = getDataForKey(props.data as Object, props.block.getDataKey("key") as string);
			}
			dynamicStyles = {
				[props.block.getDataKey("property") as string]: value,
			};
		}
		props.block
			.getDynamicValues()
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
						props.defaultProps,
						getComponentDataValue,
					);
				} else if (dataKeyObj.comesFrom === "componentData") {
					value = getComponentDataValue(dataKeyObj.key as string);
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

	if (!props.preview && props.block.getTag() === "iframe") {
		styleMap.pointerEvents = "none";
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
	let fontFamily = props.block.getStyle("fontFamily") as string;
	const fontWeight = props.block.getStyle("fontWeight") as string;
	if (!fontFamily && fontWeight) {
		let parent = props.block.getParentBlock();
		while (parent) {
			const parentFont = parent.getStyle("fontFamily") as string;
			if (parentFont) {
				fontFamily = parentFont;
				break;
			}
			parent = parent.getParentBlock();
		}
	}
	setFont(fontFamily, fontWeight);
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
	isMounted.value = true;
});

onUnmounted(() => {
	const componentId = extractComponentId(props.block);
	if (componentId) {
		componentStore.deleteComponentData(componentId, uidToUse);
	}
});

const allResolvedProps = computed(() => {
	const defaultProps = Object.entries(props.defaultProps || {}).reduce(
		(acc, [key, value]) => {
			acc[key] = value.value;
			return acc;
		},
		{} as Record<string, any>,
	);

	const blockProps = Object.entries({
		...props.block.getBlockProps(),
	}).reduce(
		(acc, [key]) => {
			acc[key] = getPropValue(
				key,
				props.block,
				getDataScriptValue,
				props.defaultProps,
				getComponentDataValue,
			);
			return acc;
		},
		{} as Record<string, any>,
	);

	const parentProps = Object.entries(getParentProps(props.block)).reduce(
		(acc, [key, value]) => {
			acc[key] = getPropValue(
				key,
				value.block!,
				getDataScriptValue,
				props.defaultProps,
				getComponentDataValue,
			);
			return acc;
		},
		{} as Record<string, any>,
	);

	return {
		...parentProps,
		...blockProps,
		...defaultProps,
	};
});

const fetchingComponentDetails = computed(() => {
	return (
		componentStore.fetchingComponentVersion.has(props.block.componentVersion || "") ||
		componentStore.fetchingComponent.has(props.block.extendedFromComponent || "")
	);
});

watch(
	[
		() => props.block.extendedFromComponent,
		() => props.block.componentVersion,
		() => canvasStore.editingMode,
		() => props.componentData,
		() => uidToUse,
		fetchingComponentDetails,
		allResolvedProps,
	],
	([componentId, , , , , fetchingComponentDetails, allResolvedProps]) => {
		// can use extractComponentId but below code is more efficient
		if (!componentId) {
			return;
		}
		if (fetchingComponentDetails) {
			return;
		}
		componentStore.setComponentData(componentId, allResolvedProps, uidToUse, props.block.componentVersion);
	},
	{ immediate: true },
);

const isEditable = computed(() => {
	// to ensure it is right block and not on different breakpoint
	return (
		canvasStore.editableBlock === props.block &&
		canvasStore.activeCanvas?.activeBreakpoint === props.breakpoint
	);
});

const hiddenDueToVisibilityCondition = computed(() => {
	const visibilityCondition = props.block.getVisibilityCondition();
	const key = visibilityCondition?.key;
	const comesFrom = visibilityCondition?.comesFrom || "dataScript";
	if (!key) return false;
	if (comesFrom == "dataScript") {
		const value = getDataScriptValue(key as string);
		return !Boolean(value);
	} else if (comesFrom == "componentData") {
		const value = getComponentDataValue(key as string);
		return !Boolean(value);
	} else {
		const value = getPropValue(
			key as string,
			props.block,
			getDataScriptValue,
			props.defaultProps,
			getComponentDataValue,
		);
		return !Boolean(value);
	}
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
				if (props.block.isImage()) {
					// delay setting selected state for images to accecpt double click for triggering image upload in editor
					setTimeout(() => {
						isSelected.value = true;
					}, 200);
				} else {
					isSelected.value = true;
				}
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
