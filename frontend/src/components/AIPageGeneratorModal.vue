<template>
	<Dialog v-model="showDialog" :options="{ title, size: 'lg' }">
		<template #body-content>
			<div class="flex flex-col gap-3">
				<Textarea
					v-model="prompt"
					:rows="4"
					variant="outline"
					:placeholder="placeholder"
					@keydown.meta.enter="handleSubmit"
					@keydown.ctrl.enter="handleSubmit" />

				<div v-if="errorMessage" class="text-ink-red-9 rounded-lg bg-surface-red-1 p-3 text-sm">
					{{ errorMessage }}
				</div>

				<WebPagePresetPicker v-if="mode === 'generate'" v-model="selectedPreset" :showLabel="false" />
			</div>
		</template>

		<template #actions>
			<div class="flex w-full items-center justify-between gap-2">
				<FormControl
					type="select"
					:options="[{ label: 'AI Model', value: '_', disabled: true }, ...modelOptions]"
					v-model="selectedModel"
					class="text-xs" />
				<div class="flex items-center gap-2">
					<Button variant="solid" @click="handleSubmit" :disabled="!canGenerate || generating">
						<template v-if="generating">
							<FeatherIcon name="loader" class="h-4 w-4 animate-spin" />
							{{ progressMessage || (mode === "modify" ? "Modifying…" : "Generating…") }}
						</template>
						<template v-else>{{ mode === "modify" ? "Modify" : "Generate" }}</template>
					</Button>
				</div>
			</div>
		</template>
	</Dialog>

	<Teleport to="body">
		<Transition name="slide-up">
			<div
				v-if="(generating || progressMessage) && !showDialog"
				class="fixed left-1/2 top-16 z-[1000] -translate-x-1/2">
				<div
					class="flex items-center gap-3 rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-2.5 shadow-lg">
					<FeatherIcon
						:name="generating ? 'loader' : 'check-circle'"
						:class="[generating ? 'animate-spin text-ink-gray-7' : 'text-ink-green-3', 'h-4 w-4']" />
					<span class="text-sm font-medium text-ink-gray-9">
						{{ progressMessage || (mode === "modify" ? "Modifying section…" : "Generating page…") }}
					</span>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import WebPagePresetPicker from "@/components/WebPagePresetPicker.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { useThrottleFn } from "@vueuse/core";
import { createResource, FeatherIcon, FormControl, Textarea } from "frappe-ui";
import yaml from "js-yaml";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

interface Preset {
	id: string;
	name: string;
	description: string;
	icon: string;
	category: string;
}

interface AIModel {
	name: string;
	label: string;
	max_tokens: number;
}

interface AIProvider {
	provider: string;
	models: AIModel[];
}

interface SelectOption {
	label: string;
	value: string;
}

interface StreamData {
	chunk?: string;
	task_type?: string;
	block_id?: string;
}

interface ProgressData {
	message?: string;
	task_type?: string;
	block_id?: string;
}

interface CompleteData {
	model_used?: string;
	task_tier?: "simple" | "complex";
}

const props = withDefaults(
	defineProps<{
		modelValue: boolean;
		pageId: string;
		mode?: "generate" | "modify";
		blockContext?: Record<string, any> | null;
	}>(),
	{ mode: "generate", blockContext: null },
);

const emit = defineEmits<{
	(e: "update:modelValue", value: boolean): void;
	(e: "update:blockContext", value: Record<string, any> | null): void;
	(e: "generated"): void;
	(e: "streaming", block: BlockOptions): void;
	(e: "modified"): void;
	(e: "modifyStreaming", block: BlockOptions): void;
	(e: "openSettings"): void;
	(e: "generating", isGenerating: boolean): void;
}>();

const showDialog = computed({
	get: () => props.modelValue,
	set: (v) => emit("update:modelValue", v),
});

const prompt = ref("");
const generating = ref(false);
const errorMessage = ref("");
const progressMessage = ref("");
const streamingContent = ref("");
const remoteTaskType = ref<string | null>(null);
const remoteBlockId = ref<string | null>(null);
const availableModels = ref<AIProvider[]>([]);
const selectedPreset = ref<Preset | null>(null);
const selectedModel = ref("");
const currentProviderModels = computed(() => {
	const provider = builderSettings.doc?.ai_model;
	if (!provider) return [];
	const found = availableModels.value.find((p) => p.provider === provider);
	return found ? found.models : [];
});

watch(
	currentProviderModels,
	(models) => {
		if (models.length > 0 && !selectedModel.value) {
			selectedModel.value = models[0].name;
		}
	},
	{ immediate: true },
);

const modelOptions = computed<SelectOption[]>(() => {
	return currentProviderModels.value.map((m) => ({ label: m.label, value: m.name }));
});

const builderStore = useBuilderStore();
const canGenerate = computed(
	() => prompt.value.trim() !== "" && builderStore.isAIEnabled && !generating.value,
);

const TEXT_ELEMENTS = ["h1", "h2", "h3", "p", "span"];

const title = computed(() => {
	if (props.mode === "generate") return "Generate with AI";
	const el = props.blockContext?.element;
	if (typeof el === "string" && TEXT_ELEMENTS.includes(el)) return "Rewrite with AI";
	if (el === "img") return "Replace Image with AI";
	return "Modify with AI";
});

const placeholder = computed(() => {
	if (props.mode === "generate") return "Describe the page you want to create…";
	const el = props.blockContext?.element;
	if (typeof el === "string" && TEXT_ELEMENTS.includes(el))
		return "Describe how you want to rewrite this text…";
	if (el === "img") return "Describe the new image you want…";
	return "Describe how you want to modify this section…";
});

const taskType = computed(() => {
	if (props.mode !== "modify" || !props.blockContext) return null;
	const el = props.blockContext.element;
	if (typeof el === "string" && TEXT_ELEMENTS.includes(el)) return "rewrite_text";
	if (el === "img") return "replace_image";
	return null;
});

function buildPrompt(base: string) {
	const preset = selectedPreset.value;
	return preset ? `${base}\n\nDESIGN STYLE: ${preset.name}. ${preset.description}` : base;
}

function convertYAMLtoBlock(yamlBlock: Record<string, any>): BlockOptions {
	if (!yamlBlock || typeof yamlBlock !== "object" || Array.isArray(yamlBlock)) return yamlBlock;
	const ensureObj = (val: any) => (val && typeof val === "object" && !Array.isArray(val) ? val : {});
	const ensureArray = (val: any) => (Array.isArray(val) ? val : []);
	const block: BlockOptions = {
		element: yamlBlock.el || "div",
		blockName: yamlBlock.name || "",
		baseStyles: ensureObj(yamlBlock.style),
		attributes: ensureObj(yamlBlock.attrs),
		mobileStyles: ensureObj(yamlBlock.m_style),
		tabletStyles: ensureObj(yamlBlock.t_style),
		classes: ensureArray(yamlBlock.classes),
	};
	if (yamlBlock.id) block.blockId = yamlBlock.id;
	if (yamlBlock.text) block.innerText = yamlBlock.text;
	block.children = Array.isArray(yamlBlock.c) ? yamlBlock.c.map(convertYAMLtoBlock) : [];
	return block;
}

function getValidPartialYAML(yamlStr: string): any {
	let cleaned = yamlStr.trim();
	if (cleaned.startsWith("```")) {
		const lines = cleaned.split("\n");
		lines.shift();
		if (lines.at(-1)?.startsWith("```")) lines.pop();
		cleaned = lines.join("\n");
	}
	try {
		return yaml.load(cleaned);
	} catch {
		const lines = cleaned.split("\n");
		for (let i = lines.length - 1; i > 0; i--) {
			try {
				const parsed = yaml.load(lines.slice(0, i).join("\n"));
				if (parsed) return parsed;
			} catch {}
		}
	}
	return null;
}

function parseBlock(raw: string): BlockOptions | null {
	const parsed = getValidPartialYAML(raw);
	if (!parsed) return null;
	const block = Array.isArray(parsed) ? parsed[0] : parsed;
	return block && typeof block === "object" && block.el ? convertYAMLtoBlock(block) : null;
}

function resetState() {
	generating.value = true;
	errorMessage.value = "";
	progressMessage.value = "Initializing…";
	streamingContent.value = "";
	showDialog.value = false;
}

function handleError(error: unknown, fallback: string) {
	generating.value = false;
	progressMessage.value = "";
	showDialog.value = true;
	errorMessage.value = error instanceof Error ? error.message : fallback;
}

async function runTask(type: "generate" | "modify", customParams: Record<string, any> = {}) {
	resetState();
	const isModify = type === "modify" || props.mode === "modify";
	const url = `builder.ai_page_generator.${isModify ? "modify_section" : "generate_page"}_from_prompt`;

	try {
		await createResource({
			url,
			makeParams: () => ({
				prompt: buildPrompt(prompt.value),
				page_id: props.pageId,
				model: selectedModel.value,
				...customParams,
			}),
		}).submit();
	} catch (e) {
		handleError(e, `An error occurred while ${isModify ? "modifying" : "generating"}`);
	}
}

const handleSubmit = () => {
	if (props.mode === "modify") {
		runTask("modify", {
			block_context: JSON.stringify(props.blockContext),
			task_type: taskType.value,
		});
	} else {
		runTask("generate");
	}
};

async function executeDirect(
	block: Record<string, any>,
	type: "rewrite_text" | "replace_image",
	customPrompt?: string,
) {
	emit("update:blockContext", block);
	runTask("modify", {
		prompt: customPrompt || (type === "rewrite_text" ? "Improve this text" : "Replace image"),
		block_context: JSON.stringify(block),
		task_type: type,
	});
}

function processStreaming() {
	const block = parseBlock(streamingContent.value);
	if (block) {
		block.originalElement = "body";
		block.blockId = block.blockId || "root";
		emit("streaming", block);
	}
}

function processModifyStreaming() {
	const effectiveTaskType = remoteTaskType.value || taskType.value;
	const effectiveBlockId = remoteBlockId.value || props.blockContext?.blockId;

	if (effectiveTaskType === "rewrite_text") {
		emit("modifyStreaming", {
			innerHTML: streamingContent.value.trim().replace(/^"|"$/g, ""),
			blockId: effectiveBlockId,
		});
		return;
	}
	if (effectiveTaskType === "replace_image") {
		const parsed = getValidPartialYAML(streamingContent.value);
		emit("modifyStreaming", { attributes: { src: parsed }, blockId: effectiveBlockId });
		return;
	}
	const block = parseBlock(streamingContent.value);
	if (block) {
		block.blockId = effectiveBlockId;
		emit("modifyStreaming", block);
	}
}

const throttledStreaming = useThrottleFn(processStreaming, 300);
const throttledModifyStreaming = useThrottleFn(processModifyStreaming, 300);

function makeHandlers(isModify: boolean) {
	const onProgress = (data: ProgressData) => {
		generating.value = true;
		if (data.message) progressMessage.value = data.message;
		if (data.task_type) remoteTaskType.value = data.task_type;
		if (isModify && data.block_id) remoteBlockId.value = data.block_id;
	};

	const onStream = (data: StreamData) => {
		generating.value = true;
		if (!data.chunk) return;
		streamingContent.value += data.chunk;
		if (data.task_type) remoteTaskType.value = data.task_type;
		if (data.block_id) remoteBlockId.value = data.block_id;
		const canThrottle = !isModify || !["rewrite_text", "replace_image"].includes(remoteTaskType.value ?? "");
		if (canThrottle) (isModify ? throttledModifyStreaming : throttledStreaming)();
	};

	const onComplete = (_data: CompleteData) => {
		generating.value = false;
		progressMessage.value = "Page generation completed";
		setTimeout(() => (progressMessage.value = ""), 2000);
		if (isModify) {
			processModifyStreaming();
			emit("modified");
		} else {
			processStreaming();
			emit("generated");
		}
		prompt.value = "";
		remoteTaskType.value = null;
		remoteBlockId.value = null;
	};

	const onError = (data: { message?: string }) => {
		generating.value = false;
		progressMessage.value = "";
		showDialog.value = true;
		errorMessage.value =
			data.message || `An error occurred while ${isModify ? "modifying the section" : "generating the page"}`;
		remoteTaskType.value = null;
		remoteBlockId.value = null;
	};

	return { onProgress, onStream, onComplete, onError };
}

const generateHandlers = makeHandlers(false);
const modifyHandlers = makeHandlers(true);

const eventName = (base: string) => (props.pageId ? `${base}_${props.pageId}` : base);

const listeners = {
	ai_generation_progress: generateHandlers.onProgress,
	ai_generation_stream: generateHandlers.onStream,
	ai_generation_complete: generateHandlers.onComplete,
	ai_generation_error: generateHandlers.onError,
	ai_modify_progress: modifyHandlers.onProgress,
	ai_modify_stream: modifyHandlers.onStream,
	ai_modify_complete: modifyHandlers.onComplete,
	ai_modify_error: modifyHandlers.onError,
};

function attachListeners() {
	Object.entries(listeners).forEach(([evt, handler]) => {
		builderStore.realtime.on(eventName(evt), handler);
	});
}

function detachListeners() {
	Object.entries(listeners).forEach(([evt, handler]) => {
		builderStore.realtime.off(eventName(evt), handler);
	});
}

onMounted(() => {
	attachListeners();
	createResource({
		url: "builder.ai_page_generator.get_ai_models",
		auto: true,
		onSuccess: (data: AIProvider[]) => (availableModels.value = data),
	});
});

onUnmounted(detachListeners);

watch(
	() => props.pageId,
	() => {
		detachListeners();
		attachListeners();
	},
);
watch(generating, (v) => emit("generating", v));
watch(showDialog, (v) => {
	if (v) {
		errorMessage.value = "";
		progressMessage.value = "";
		streamingContent.value = "";
	}
});

defineExpose({ executeDirect });
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
	transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
	opacity: 0;
	transform: translate(-50%, -20px);
}
</style>
