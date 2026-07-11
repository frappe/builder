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
import { BlockValueResolver } from "@/utils/blockValueResolver";
import componentController from "@/utils/componentController.js";
import { setFont } from "@/utils/fontManager";
import { extractComponentId } from "@/utils/helpers";
import type { BlockClientScriptEmulator } from "@/utils/scriptSandbox";
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
	},
);

const editingComponentId = computed(() =>
	canvasStore.fragmentData.fragmentType === "component" &&
	!props.block.getParentBlock() &&
	props.block === canvasStore.fragmentData.block
		? canvasStore.fragmentData.fragmentId
		: null,
);

const resolvedComponentData = computed(() => {
	if (editingComponentId.value && !props.block.getParentBlock()) {
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

const isSelected = ref(false);

const isHovered = computed(() => {
	return !props.preview && canvasStore.activeCanvas?.hoveredBlock === props.block.blockId;
});

const selectedInCanvas = computed(() => {
	return !props.preview && Boolean(canvasStore.activeCanvas?.isSelected(props.block));
});

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

const valueResolver = new BlockValueResolver({
	block: () => props.block,
	data: () => props.data ?? null,
	componentData: () => resolvedComponentData.value ?? null,
	defaultProps: () => props.defaultProps ?? null,
});

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
		attribs.componentData = resolvedComponentData.value;
		attribs.defaultProps = props.defaultProps;
	}

	valueResolver.applyDynamicValues("attribute", attribs);

	if (props.block.isInput()) {
		attribs.readonly = true;
	}

	return attribs;
});

const canvasProps = !props.preview ? (inject("canvasProps") as CanvasProps) : null;
const emulateBlockClientScript = inject<BlockClientScriptEmulator>(
	"emulateBlockClientScript",
	() => () => {},
);

const target = computed(() => {
	if (!component.value) return null;
	if (component.value instanceof HTMLElement || component.value instanceof SVGElement) {
		return component.value;
	} else {
		return component.value.component;
	}
});

const styles = computed(() => {
	const dynamicStyles = valueResolver.applyDynamicValues("style", {}) as BlockStyleMap;

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
	return valueResolver.getResolvedProps();
});

const fetchingComponentDetails = computed(() => {
	return (
		componentStore.fetchingComponentVersion.has(props.block.componentVersion || "") ||
		componentStore.fetchingComponent.has(props.block.extendedFromComponent || "")
	);
});
const componentDataReady = ref(false);

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
		componentDataReady.value = false;
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

watch(resolvedComponentData, () => {
	componentDataReady.value = true;
});

const blockClientScript = computed(() => {
	const clientScript = props.block.extendedFromComponent
		? props.block.referenceComponent?.clientScript
		: props.block.clientScript;
	return {
		javascript: clientScript?.js || "",
		css: clientScript?.css || "",
	};
});

watch(
	[
		target,
		blockClientScript,
		resolvedComponentData,
		allResolvedProps,
		() => builderSettings.doc?.execute_block_scripts_in_editor,
		() => pageStore.settingPage,
		componentDataReady,
	],
	([element, clientScript, componentData, resolvedProps, , settingPage, dataReady], _, onCleanup) => {
		if (!element || !clientScript) return;
		const waitsForComponentData = Boolean(props.block.extendedFromComponent);
		const cleanup = emulateBlockClientScript({
			key: uidToUse,
			element: element as HTMLElement,
			breakpoint: props.breakpoint,
			css: clientScript.css ?? "",
			javascript:
				settingPage || (waitsForComponentData && !editingComponentId.value && !dataReady)
					? ""
					: clientScript.javascript ?? "",
			componentData: componentData ?? {},
			props: resolvedProps,
		});
		onCleanup(cleanup);
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
	return valueResolver.isHiddenByVisibilityCondition();
});

watch(
	selectedInCanvas,
	(selected, _, onCleanup) => {
		if (!selected || !props.block.isImage()) {
			isSelected.value = selected;
			return;
		}

		// Preserve double-click image uploads before showing the selection editor.
		const timeout = setTimeout(() => {
			isSelected.value = true;
		}, 200);
		onCleanup(() => clearTimeout(timeout));
	},
	{ immediate: true },
);

// Note: All the block event listeners are delegated to parent for better scalability
</script>
