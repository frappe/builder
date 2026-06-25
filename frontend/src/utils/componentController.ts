import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import { useLatestRequest } from "@/composables/useLatestRequest";
import { BuilderComponent } from "@/types/doctypes";
import { createResource } from "frappe-ui";
import { computed, reactive, watch } from "vue";
import { parseJSONWithFallback } from "./helpers";

const { run: runLatestRequest } = useLatestRequest();

type ComponentDocDraft = Pick<
	BuilderComponent,
	"component_props" | "component_data_script" | "component_js" | "component_css"
> & {
	component_data_preview: Record<string, any>;
};

const EMPTY_DRAFT: ComponentDocDraft = {
	component_props: {},
	component_data_script: "",
	component_js: "",
	component_css: "",
	component_data_preview: {},
};

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();

const currentComponentId = computed(() => canvasStore.fragmentData?.fragmentId ?? "");
const componentDocDraft = reactive<ComponentDocDraft>({ ...EMPTY_DRAFT });

function markCanvasDirty(dirty: boolean = true) {
	canvasStore.activeCanvas?.toggleDirty(dirty);
}

function cloneComponentDocFields(
	doc: ComponentDocDraft,
	preview: Record<string, any> = {},
): ComponentDocDraft {
	return {
		component_props: parseJSONWithFallback(doc.component_props, {}),
		component_data_script: doc.component_data_script ?? "",
		component_js: doc.component_js ?? "",
		component_css: doc.component_css ?? "",
		component_data_preview: parseJSONWithFallback(preview, {}),
	};
}

function getOriginalDoc() {
	const componentId = currentComponentId.value;
	if (!componentId) return null;
	return componentStore.getComponent(componentId);
}

function loadDraftFromOriginal() {
	const original = getOriginalDoc();
	if (!original) {
		Object.assign(componentDocDraft, EMPTY_DRAFT);
		return;
	}

	const componentId = currentComponentId.value;
	const preview =
		componentStore.componentData[componentId]?.[canvasStore.fragmentData.block?.blockId ?? ""] ?? {};
	Object.assign(componentDocDraft, cloneComponentDocFields(original, preview));
}

function applyDraftToOriginal() {
	const original = getOriginalDoc();
	if (!original) return;

	const cloned = cloneComponentDocFields(componentDocDraft);
	original.component_props = cloned.component_props;
	original.component_data_script = cloned.component_data_script;
	original.component_js = cloned.component_js;
	original.component_css = cloned.component_css;
}

const componentDataPreview = computed(() => {
	if (!currentComponentId.value) return {};
	return componentDocDraft.component_data_preview ?? {};
});

const componentProps = computed(() => {
	if (!currentComponentId.value) return {};
	return componentDocDraft.component_props ?? {};
});

const componentDataScript = computed(() => {
	if (!currentComponentId.value) return "";
	return componentDocDraft.component_data_script ?? "";
});

const componentJavaScript = computed(() => {
	if (!currentComponentId.value) return "";
	return componentDocDraft.component_js ?? "";
});

const componentCSS = computed(() => {
	if (!currentComponentId.value) return "";
	return componentDocDraft.component_css ?? "";
});

const componentController = {
	currentComponentId,
	componentDataPreview,
	componentProps,
	componentDataScript,
	componentJavaScript,
	componentCSS,

	getComponentProps: () => componentProps.value,

	setComponentProps: (props: BlockProps) => {
		if (!currentComponentId.value) return;
		componentDocDraft.component_props = props;
		canvasStore.fragmentData.block?.setBlockProps(props);
		markCanvasDirty(true);
	},

	getComponentDataScript: () => componentDataScript.value,

	setComponentDataScript: (script: string) => {
		if (!currentComponentId.value) return;
		componentDocDraft.component_data_script = script;
		markCanvasDirty(true);
	},

	getComponentClientScript: (type: "js" | "css" = "js") => {
		return type === "js" ? componentJavaScript.value : componentCSS.value;
	},

	setComponentClientScript: (script: string, type: "js" | "css" = "js") => {
		if (!currentComponentId.value) return;
		componentDocDraft[type === "js" ? "component_js" : "component_css"] = script;
		markCanvasDirty(true);
	},

	getComponentDataPreview: () => componentDataPreview.value,

	resetComponentDoc: async () => {
		loadDraftFromOriginal();
		await componentController.setComponentDataPreview();
	},

	applyComponentDoc: () => {
		applyDraftToOriginal();
	},

	setComponentDataPreview: async () => {
		const componentId = currentComponentId.value;
		if (!componentId) return;

		// convert props to {propName: propValue} format
		const props = Object.entries((componentDocDraft.component_props as BlockProps) ?? {}).reduce(
			(acc: Record<string, any>, [key, value]: [string, BlockProps[string]]) => {
				acc[key] = value.value ?? value.propOptions?.options?.defaultValue;
				return acc;
			},
			{} as Record<string, any>,
		);
		const script = componentDocDraft.component_data_script ?? "";
		const requestKey = `${componentId}::preview`;
		const result = await runLatestRequest(requestKey, () =>
			createResource({
				url: "builder.api.get_component_data",
				method: "POST",
				auto: false,
			})
				.submit({
					component_name: componentId,
					props: JSON.stringify(props),
					script,
				})
				.then((data: { [key: string]: any }) => data ?? {})
				.catch((e: { message: string }) => {
					console.error("Failed to execute component data script:", e.message);
					return {};
				}),
		);
		if (result.stale || componentId !== currentComponentId.value) return;

		componentDocDraft.component_data_preview = result.value;
	},
};

watch(
	currentComponentId,
	(componentId) => {
		if (componentId) {
			loadDraftFromOriginal();
		} else {
			Object.assign(componentDocDraft, EMPTY_DRAFT);
		}
	},
	{ immediate: true },
);

watch(
	[currentComponentId, componentProps, componentDataScript, () => canvasStore.editingMode],
	async () => {
		if (canvasStore.editingMode != "fragment") return;
		if (currentComponentId.value) {
			await componentController.setComponentDataPreview();
		}
	},
	{ deep: true, immediate: true },
);

watch(
	[currentComponentId, () => canvasStore.editingMode],
	() => {
		if (canvasStore.editingMode != "fragment") return;
		const initialProps = componentController.getComponentProps();
		canvasStore.fragmentData.block?.setBlockProps(initialProps);
		markCanvasDirty(false);
	},
	{ immediate: true },
);

export default componentController;
