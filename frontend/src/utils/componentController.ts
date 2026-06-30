import { useLatestRequest } from "@/composables/useLatestRequest";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import { BuilderComponent } from "@/types/doctypes";
import { createResource } from "frappe-ui";
import { computed, reactive, watch } from "vue";
import { parseJSONWithFallback } from "./helpers";

const { run: runLatestRequest } = useLatestRequest();

export type ComponentDocDraft = Omit<
	BuilderComponent,
	"name" | "creation" | "modified" | "owner" | "modified_by"
> & {
	component_data_preview: Record<string, any>;
};

const EMPTY_DRAFT: ComponentDocDraft = {
	component_name: "",
	component_data_script: "",
	component_data_preview: {},
};

const canvasStore = useCanvasStore();
const componentStore = useComponentStore();

const currentComponentId = computed(() =>
	canvasStore.fragmentData.fragmentType === "component" ? canvasStore.fragmentData.fragmentId ?? "" : "",
);
const componentDocDraft = reactive<ComponentDocDraft>({ ...EMPTY_DRAFT });

function markCanvasDirty(dirty: boolean = true) {
	canvasStore.activeCanvas?.toggleDirty(dirty);
}

function cloneComponentDocFields(
	doc: BuilderComponent,
	preview: Record<string, any> = {},
): ComponentDocDraft {
	return {
		component_data_script: doc.component_data_script ?? "",
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

const componentDataPreview = computed(() => {
	if (!currentComponentId.value) return {};
	return componentDocDraft.component_data_preview ?? {};
});

const componentProps = computed(() => {
	if (!currentComponentId.value) return {};
	return canvasStore.fragmentData.block?.props ?? {};
});

const componentDataScript = computed(() => {
	if (!currentComponentId.value) return "";
	return componentDocDraft.component_data_script ?? "";
});

const componentController = {
	currentComponentId,
	componentDataPreview,
	componentProps,
	componentDataScript,

	getComponentDataScript: () => componentDataScript.value,

	setComponentDataScript: (script: string) => {
		if (!currentComponentId.value) return;
		componentDocDraft.component_data_script = script;
		markCanvasDirty(true);
	},

	getComponentDataPreview: () => componentDataPreview.value,

	resetComponentDoc: async () => {
		loadDraftFromOriginal();
		await componentController.setComponentDataPreview();
	},

	applyComponentDoc: () => {
		componentStore.setComponentDraft(currentComponentId.value, componentDocDraft);
	},

	setComponentDataPreview: async () => {
		const componentId = currentComponentId.value;
		if (!componentId) return;

		// convert props to {propName: propValue} format
		const props = Object.entries(componentProps.value).reduce(
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
	(componentId, oldComponentId) => {
		if (componentId) {
			loadDraftFromOriginal();
		} else {
			Object.assign(componentDocDraft, EMPTY_DRAFT);
		}
		if (oldComponentId) {
			componentStore.deleteComponentDraft(oldComponentId);
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
		markCanvasDirty(false);
	},
	{ immediate: true },
);

export default componentController;
