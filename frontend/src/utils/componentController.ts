import useCanvasStore from "@/stores/canvasStore";
import useComponentStore, { COMPONENT_DATA_FRAGMENT_KEY } from "@/stores/componentStore";
import { BuilderComponent } from "@/types/doctypes";
import { markCanvasDirty } from "@/utils/useCanvasUtils";
import { createResource } from "frappe-ui";
import { computed, reactive, watch } from "vue";

type ComponentDocDraft = Pick<
	BuilderComponent,
	"component_props" | "component_vars" | "component_data_script" | "component_js" | "component_css"
>;

const EMPTY_DRAFT: ComponentDocDraft = {
	component_props: {},
	component_vars: {},
	component_data_script: "",
	component_js: "",
	component_css: "",
};

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();

const currentComponentId = computed(() => canvasStore.fragmentData?.fragmentId ?? "");
const componentDocDraft = reactive<ComponentDocDraft>({ ...EMPTY_DRAFT });

function cloneJsonField<T>(value: T | undefined, fallback: T): T {
	if (value === undefined || value === null) {
		return fallback;
	}
	// JSON fields may be Vue reactive proxies; structuredClone cannot clone those.
	return JSON.parse(JSON.stringify(value)) as T;
}

function cloneComponentDocFields(doc: BuilderComponent): ComponentDocDraft {
	return {
		component_props: cloneJsonField(doc.component_props, {}),
		component_vars: cloneJsonField(doc.component_vars, {}),
		component_data_script: doc.component_data_script ?? "",
		component_js: doc.component_js ?? "",
		component_css: doc.component_css ?? "",
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

	const cloned = cloneComponentDocFields(original);
	componentDocDraft.component_props = cloned.component_props;
	componentDocDraft.component_vars = cloned.component_vars;
	componentDocDraft.component_data_script = cloned.component_data_script;
	componentDocDraft.component_js = cloned.component_js;
	componentDocDraft.component_css = cloned.component_css;
}

function applyDraftToOriginal() {
	const original = getOriginalDoc();
	if (!original) return;

	const cloned = cloneComponentDocFields(componentDocDraft as BuilderComponent);
	original.component_props = cloned.component_props;
	original.component_vars = cloned.component_vars;
	original.component_data_script = cloned.component_data_script;
	original.component_js = cloned.component_js;
	original.component_css = cloned.component_css;
}

const componentDataPreview = computed(() => {
	const componentId = currentComponentId.value;
	if (!componentId) return {};
	return componentStore.componentData[componentId]?.[COMPONENT_DATA_FRAGMENT_KEY] ?? {};
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
		componentController.setComponentDataPreview();
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
		componentController.setComponentDataPreview();
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

	resetComponentDoc: () => {
		loadDraftFromOriginal();
		componentController.setComponentDataPreview();
	},

	applyComponentDoc: () => {
		applyDraftToOriginal();
	},

	setComponentDataPreview: async () => {
		const componentId = currentComponentId.value;
		if (componentId) {
			const data = await componentController.executeComponentDataScript();
			if (!componentStore.componentData[componentId]) {
				componentStore.componentData[componentId] = {};
			}
			componentStore.componentData[componentId][COMPONENT_DATA_FRAGMENT_KEY] = data;
		}
	},

	executeComponentDataScript: async () => {
		const componentId = currentComponentId.value;
		return createResource({
			url: "builder.api.get_component_data",
			method: "GET",
			params: {
				component_name: componentId,
				props: JSON.stringify(componentController.getComponentProps()),
				script: componentController.getComponentDataScript(),
			},
		})
			.fetch()
			.then((data: { [key: string]: any }) => data)
			.catch((e: { message: string }) => {
				console.error("Failed to execute component data script:", e.message);
				return {};
			});
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
