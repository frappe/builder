import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import { useLatestRequest } from "@/composables/useLatestRequest";
import { BuilderComponent } from "@/types/doctypes";
import { markCanvasDirty } from "@/utils/useCanvasUtils";
import { createResource } from "frappe-ui";
import { computed, reactive, watch } from "vue";
import { parseJSONWithFallback } from "./helpers";

const { run: runLatestRequest } = useLatestRequest();

type ComponentDocDraft = Pick<
	BuilderComponent,
	"component_props" | "component_vars" | "component_data_script" | "component_js" | "component_css"
> & {
	component_data_preview: Record<string, any>;
};

const EMPTY_DRAFT: ComponentDocDraft = {
	component_props: {},
	component_vars: {},
	component_data_script: "",
	component_js: "",
	component_css: "",
	component_data_preview: {},
};

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();

const currentComponentId = computed(() => canvasStore.fragmentData?.fragmentId ?? "");
const componentDocDraft = reactive<ComponentDocDraft>({ ...EMPTY_DRAFT });


function cloneComponentDocFields(
	doc: ComponentDocDraft,
	preview: Record<string, any> = {},
): ComponentDocDraft {
	return {
		component_props: parseJSONWithFallback(doc.component_props, {}),
		component_vars: parseJSONWithFallback(doc.component_vars, {}),
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
	original.component_vars = cloned.component_vars;
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

const componentVars = computed(() => {
	if (!currentComponentId.value) return {};
	return componentDocDraft.component_vars ?? {};
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
	componentVars,
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

	getComponentVars: () => componentVars.value,

	setComponentVars: (vars: BlockVars) => {
		if (!currentComponentId.value) return;
		componentDocDraft.component_vars = vars;
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

		const props = componentDocDraft.component_props ?? {};
		const script = componentDocDraft.component_data_script ?? "";
		const requestKey = `${componentId}::preview`;
		const result = await runLatestRequest(requestKey, () =>
			createResource({
				url: "builder.api.get_component_data",
				method: "GET",
				auto: false,
			})
				.fetch({
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
	[currentComponentId, componentProps, componentDataScript],
	async () => {
		if (currentComponentId.value) {
			await componentController.setComponentDataPreview();
		}
	},
	{ deep: true, immediate: true },
);

watch(
	currentComponentId,
	() => {
		const initialProps = componentController.getComponentProps();
		canvasStore.fragmentData.block?.setBlockProps(initialProps);
		markCanvasDirty(false);
	},
	{ immediate: true },
);

export default componentController;
