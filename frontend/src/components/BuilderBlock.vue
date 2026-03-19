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
			:block-data="cumulativeBlockData"
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
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { setFont } from "@/utils/fontManager";
import {
	executeBlockClientScriptRestricted,
	executeBlockClientScriptUnrestricted,
	getDataForKey,
	getParentProps,
	getPropValue,
} from "@/utils/helpers";
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
import { builderSettings } from "@/data/builderSettings";
import fetchBlockData from "@/data/blockData";
import usePageStore from "@/stores/pageStore";
import { toast } from "vue-sonner";
import { useBlockDataStore, useBlockUidStore } from "@/stores/blockStore";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const component = ref<HTMLElement | InstanceType<typeof TextBlock> | null>(null);
const attrs = useAttrs();
const editor = ref<InstanceType<typeof BlockEditor> | null>(null);
const isMounted = ref(false);

const pageStore = usePageStore();
const blockDataStore = useBlockDataStore();
const blockUidStore = useBlockUidStore();

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
		parentBlockUid?: string | null;
		repeaterIndex?: string | number | null;
	}>(),
	{
		isChildOfComponent: false,
		breakpoint: "desktop",
		preview: false,
		readonly: false,
		data: null,
		blockData: null,
		defaultProps: null,
		repeaterIndex: null,
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

// For repeater items the same Block object is used but Block Data can vary with each item
// So we need unique identifier for block data store
// Thus we use blockId for the first index and then generate new IDs for the next items
const uidToUse = !!props.repeaterIndex
	? `builder-block-${props.block.blockId}-${props.repeaterIndex}}`
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
	const RESTRICTED_ATTRIBS = ["data-block-id", "data-block-uid", "data-breakpoint"];
	let additionalAttributes: Record<string, any> = {};

	if (builderSettings.doc?.execute_block_scripts_in_editor !== "Don't Execute") {
		additionalAttributes = props.block.getCustomAttributes();
	}

	Object.keys(additionalAttributes).forEach((key) => {
		if (RESTRICTED_ATTRIBS.includes(key)) {
			delete additionalAttributes[key];
		}
	});

	const attribs = { ...additionalAttributes, ...props.block.getAttributes(), ...attrs } as {
		[key: string]: any;
	};

	if (props.block.isImage() && !props.preview) {
		if (builderStore.isDark && attribs.darkSrc) {
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
		attribs.uid = uidToUse;
		attribs.repeaterIndex = props.repeaterIndex;
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
				value = getPropValue(props.block.getDataKey("key") as string, props.block, uidToUse);
			} else if (props.block.getDataKey("comesFrom") === "blockDataScript") {
				value = getBlockDataScriptValue(props.block.getDataKey("key") as string);
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
					value = getPropValue(dataKeyObj.key as string, props.block, uidToUse);
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
				value = getPropValue(props.block.getDataKey("key") as string, props.block, uidToUse);
			} else if (props.block.getDataKey("comesFrom") === "blockDataScript") {
				value = getBlockDataScriptValue(props.block.getDataKey("key") as string);
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
					value = getPropValue(dataKeyObj.key as string, props.block, uidToUse);
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
	blockUidStore.registerBlockUid(uidToUse, props.block);
	blockUidStore.setParentUid(uidToUse, props.parentBlockUid || "root");
	isMounted.value = true;
});

const allResolvedProps = computed(() => {
	if (!isMounted.value) {
		return {};
	}
	const defaultProps = Object.entries(props.defaultProps || {}).reduce((acc, [key, value]) => {
		acc[key] = value.value;
		return acc;
	}, {} as Record<string, any>);

	const blockProps = Object.entries({
		...props.block.getBlockProps(),
	}).reduce((acc, [key]) => {
		acc[key] = getPropValue(key, props.block, uidToUse);
		return acc;
	}, {} as Record<string, any>);

	const parentProps = Object.entries(getParentProps(props.block, uidToUse)).reduce((acc, [key, value]) => {
		acc[key] = getPropValue(key, value.block!, value.blockUid);
		return acc;
	}, {} as Record<string, any>);

	return {
		...parentProps,
		...blockProps,
		...defaultProps,
	};
});

// Execute client script
watch(
	[
		component,
		allResolvedProps,
		() => props.block.getBlockClientScript(),
		() => builderSettings.doc?.execute_block_scripts_in_editor,
		() => pageStore.settingPage,
	],
	() => {
		if (pageStore.settingPage) return;

		const script = props.block.getBlockClientScript().trim();
		if (!script) return;

		const mode = builderSettings.doc?.execute_block_scripts_in_editor;
		if (mode === "Don't Execute") return;

		if (mode === "Restricted") executeBlockClientScriptRestricted(uidToUse, script, allResolvedProps.value);
		else executeBlockClientScriptUnrestricted(uidToUse, script, allResolvedProps.value);
	},
	{ immediate: true },
);

watch(
	[
		component,
		allResolvedProps,
		() => props.blockData,
		() => props.block.getBlockDataScript(),
		() => pageStore.settingPage,
		() => pageStore.routeVariables,
	],
	(_, __, onCleanup) => {
		if (pageStore.settingPage) return;

		const script = props.block.getBlockDataScript().trim();

		if (!script) {
			ownBlockData.value = {};
			blockDataStore.setBlockData(uidToUse, {}, "own");
			return;
		}

		let cancelled = false;
		onCleanup(() => {
			cancelled = true;
		});

		fetchBlockData
			.fetch({
				block_id: uidToUse,
				block_data_script: script,
				props: JSON.stringify(allResolvedProps.value),
				route_variables: pageStore.routeVariables,
			})
			.then((res: any) => {
				if (cancelled) return;

				const data = res || {};
				ownBlockData.value = data;
				blockDataStore.setBlockData(uidToUse, data, "own");
			})
			.catch((e: { exc: string | null }) => {
				if (cancelled) return;

				const error_message = e.exc?.split("\n").slice(-2)[0];
				toast.error("There was an error while fetching page data", {
					description: error_message,
				});
			});
	},
	{ immediate: true, deep: true },
);

watchEffect(() => {
	blockDataStore.setBlockData(uidToUse, props.blockData || {}, "passedDown");
});

watchEffect(() => {
	blockDataStore.setPageData(uidToUse, props.data || {});
});

watchEffect(() => {
	blockDataStore.setBlockDefaultProps(uidToUse, props.defaultProps || {});
});

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
	if (comesFrom == "blockDataScript") {
		const value = getBlockDataScriptValue(key as string);
		return !Boolean(value);
	} else if (comesFrom == "dataScript") {
		const value = getDataScriptValue(key as string);
		return !Boolean(value);
	} else {
		const value = getPropValue(key as string, props.block, uidToUse);
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

onUnmounted(() => {
	blockDataStore.clearBlockData(uidToUse);
	blockDataStore.clearPageData(uidToUse);
	blockDataStore.clearDefaultProps(uidToUse);
	blockUidStore.unregisterBlockUid(uidToUse);
	blockUidStore.clearParentUid(uidToUse);
});

// Note: All the block event listeners are delegated to parent for better scalability
</script>
