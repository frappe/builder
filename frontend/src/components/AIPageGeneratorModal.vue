<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: title,
			size: 'lg',
		}">
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
				<WebPagePresetPicker v-model="selectedPreset" v-if="mode === 'generate'" />

				<p v-if="!hasAISettings" class="text-xs text-ink-gray-6">
					Configure your AI model and API key in
					<Button variant="link" @click="$emit('openSettings')">Settings &rarr; AI</Button>
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button variant="subtle" @click="showDialog = false">Cancel</Button>
				<Button variant="solid" @click="handleSubmit" :disabled="!canGenerate || generating">
					<div class="flex items-center gap-2">
						<FeatherIcon v-if="generating" name="loader" class="h-4 w-4 animate-spin" />
						<span>
							{{
								generating
									? progressMessage || (mode === "modify" ? "Modifying..." : "Generating...")
									: mode === "modify"
										? "Modify"
										: "Generate"
							}}
						</span>
					</div>
				</Button>
			</div>
		</template>
	</Dialog>

	<!-- Floating progress indicator when generating with dialog closed -->
	<Teleport to="body">
		<Transition name="slide-up">
			<div
				v-if="(generating || progressMessage) && !showDialog"
				class="fixed left-1/2 top-16 z-[1000] -translate-x-1/2 transform">
				<div
					class="flex items-center gap-3 rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-2.5 shadow-lg">
					<FeatherIcon v-if="generating" name="loader" class="h-4 w-4 animate-spin text-ink-gray-7" />
					<FeatherIcon v-else name="check-circle" class="h-4 w-4 text-ink-green-3" />
					<span class="text-sm font-medium text-ink-gray-9">
						{{ progressMessage || (mode === "modify" ? "Modifying section..." : "Generating page...") }}
					</span>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup lang="ts">
import type Block from "@/block";
import Dialog from "@/components/Controls/Dialog.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { useThrottleFn } from "@vueuse/core";
import { createResource, FeatherIcon, Textarea } from "frappe-ui";
import yaml from "js-yaml";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import WebPagePresetPicker from "./WebPagePresetPicker.vue";

interface Preset {
	id: string;
	name: string;
	description: string;
	icon: string;
	category: string;
}

const props = withDefaults(
	defineProps<{
		modelValue: boolean;
		pageId: string;
		mode?: "generate" | "modify";
		blockContext?: Record<string, any> | null;
	}>(),
	{
		mode: "generate",
		blockContext: null,
	},
);

const emit = defineEmits<{
	(e: "update:modelValue", value: boolean): void;
	(e: "update:blockContext", value: Record<string, any> | null): void;
	(e: "generated"): void;
	(e: "streaming", block: Block): void;
	(e: "modified"): void;
	(e: "modifyStreaming", block: BlockOptions): void;
	(e: "openSettings"): void;
	(e: "generating", isGenerating: boolean): void;
}>();

const showDialog = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const prompt = ref("");
const generating = ref(false);
const errorMessage = ref("");
const progressMessage = ref("");
const streamingContent = ref("");
const selectedPreset = ref<Preset | null>(null);
const builderStore = useBuilderStore();
const remoteTaskType = ref<string | null>(null);
const remoteBlockId = ref<string | null>(null);

watch(generating, (val) => {
	emit("generating", val);
});

const hasAISettings = computed(() => {
	return builderSettings.doc?.ai_model && builderSettings.doc?.ai_api_key;
});

const TEXT_ELEMENTS = ["h1", "h2", "h3", "p", "span"];

const title = computed(() => {
	if (props.mode === "generate") return "Generate with AI";
	const el = props.blockContext?.element;
	if (TEXT_ELEMENTS.includes(el)) return "Rewrite with AI";
	if (el === "img") return "Replace Image with AI";
	return "Modify with AI";
});

const placeholder = computed(() => {
	if (props.mode === "generate") return "Describe the page you want to create...";
	const el = props.blockContext?.element;
	if (TEXT_ELEMENTS.includes(el)) return "Describe how you want to rewrite this text...";
	if (el === "img") return "Describe the new image you want...";
	return "Describe how you want to modify this section...";
});

const taskType = computed(() => {
	if (props.mode !== "modify" || !props.blockContext) return null;
	const el = props.blockContext.element;
	if (TEXT_ELEMENTS.includes(el)) return "rewrite_text";
	if (el === "img") return "replace_image";
	return null;
});

function buildPrompt(base: string): string {
	const preset = selectedPreset.value;
	return preset ? `${base}\n\nDESIGN STYLE: ${preset.name}. ${preset.description}` : base;
}

function convertYAMLtoBlock(yamlBlock: any): BlockOptions {
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
		if (lines.length > 0) lines.shift();
		if (lines.length > 0 && lines[lines.length - 1].startsWith("```")) lines.pop();
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

function parseBlock(raw: string): any | null {
	const parsed = getValidPartialYAML(raw);
	if (!parsed) return null;
	const block = Array.isArray(parsed) ? parsed[0] : parsed;
	if (block && typeof block === "object" && block.el) {
		return convertYAMLtoBlock(block);
	}
	return null;
}

const canGenerate = computed(() => {
	return prompt.value.trim() !== "" && hasAISettings.value && !generating.value;
});

const handleSubmit = () => {
	return props.mode === "modify" ? modifySection() : generatePage();
};

const generatePage = async () => {
	if (!canGenerate.value) return;

	generating.value = true;
	errorMessage.value = "";
	progressMessage.value = "Initializing...";
	streamingContent.value = "";
	showDialog.value = false;

	try {
		await createResource({
			url: "builder.ai_page_generator.generate_page_from_prompt",
			makeParams: () => ({
				prompt: buildPrompt(prompt.value),
				page_id: props.pageId,
			}),
		}).submit();
	} catch (error: any) {
		generating.value = false;
		progressMessage.value = "";
		showDialog.value = true;
		errorMessage.value = error.message || "An error occurred while generating the page";
	}
};

const modifySection = async () => {
	if (!canGenerate.value || !props.blockContext) return;

	generating.value = true;
	errorMessage.value = "";
	progressMessage.value = "Initializing...";
	streamingContent.value = "";
	showDialog.value = false;

	try {
		await createResource({
			url: "builder.ai_page_generator.modify_section_from_prompt",
			makeParams: () => ({
				prompt: buildPrompt(prompt.value),
				block_context: JSON.stringify(props.blockContext),
				page_id: props.pageId,
				task_type: taskType.value,
			}),
		}).submit();
	} catch (error: any) {
		generating.value = false;
		progressMessage.value = "";
		showDialog.value = true;
		errorMessage.value = error.message || "An error occurred while modifying the section";
	}
};

const executeDirect = async (block: any, type: "rewrite_text" | "replace_image", customPrompt?: string) => {
	generating.value = true;
	errorMessage.value = "";
	progressMessage.value = "Initializing...";
	streamingContent.value = "";
	showDialog.value = false;

	// Set modify state so handlers know what to do
	emit("update:blockContext", block);
	// We need to wait for parent to update modifiedBlockId if we want to follow the same flow
	// or we can just handle it here. PageBuilder handles modified blocks by watching the events.
	// But it needs modifyBlockId correctly set.
	// Actually, it might be better if PageBuilder sets the state and then calls this,
	// or this method takes enough info.

	const finalPrompt =
		customPrompt || (type === "rewrite_text" ? "Improve this text" : "Suggest a better image");

	try {
		await createResource({
			url: "builder.ai_page_generator.modify_section_from_prompt",
			makeParams: () => ({
				prompt: finalPrompt,
				block_context: JSON.stringify(block),
				page_id: props.pageId,
				task_type: type,
			}),
		}).submit();
	} catch (error: any) {
		generating.value = false;
		progressMessage.value = "";
		errorMessage.value = error.message || "An error occurred";
		showDialog.value = true;
	}
};

watch(showDialog, (newValue) => {
	if (newValue) {
		errorMessage.value = "";
		progressMessage.value = "";
		streamingContent.value = "";
	}
});

function applyTierLabel(data: any) {
	if (data.model_used) {
		const tierLabels: Record<string, string> = {
			simple: "fast",
			complex: "full",
		};
		progressMessage.value = `Done — ${tierLabels[data.task_tier] || ""} mode with ${data.model_used}`;
		setTimeout(() => {
			progressMessage.value = "";
		}, 2000);
	} else {
		progressMessage.value = "";
	}
}

// Throttled emitters to minimize overhead
const throttledProcessStreaming = useThrottleFn(() => {
	const block = parseBlock(streamingContent.value);
	if (block) {
		block.originalElement = "body";
		block.blockId = block.blockId || "root";
		emit("streaming", block);
	}
}, 300);

const throttledProcessModifyStreaming = useThrottleFn(() => {
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
		if (parsed && typeof parsed === "object") {
			emit("modifyStreaming", {
				attributes: parsed,
				blockId: effectiveBlockId,
			});
		}
		return;
	}

	const block = parseBlock(streamingContent.value);
	if (block) {
		block.blockId = effectiveBlockId;
		emit("modifyStreaming", block);
	}
}, 300);

const onProgress = (data: any) => {
	generating.value = true;
	if (data.message) progressMessage.value = data.message;
	if (data.task_type) remoteTaskType.value = data.task_type;
};

const onStream = (data: any) => {
	generating.value = true;
	if (!data.chunk) return;
	streamingContent.value += data.chunk;
	throttledProcessStreaming();
};

const onComplete = (data: any) => {
	generating.value = false;
	applyTierLabel(data);
	// Wait for any remaining throttled updates to resolve
	setTimeout(() => {
		emit("generated");
	}, 300);
	prompt.value = "";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
};

const onError = (data: any) => {
	generating.value = false;
	progressMessage.value = "";
	showDialog.value = true;
	errorMessage.value = data.message || "An error occurred while generating the page";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
};

const onModifyProgress = (data: any) => {
	generating.value = true;
	if (data.message) progressMessage.value = data.message;
	if (data.task_type) remoteTaskType.value = data.task_type;
	if (data.block_id) remoteBlockId.value = data.block_id;
};

const onModifyStream = (data: any) => {
	generating.value = true;
	if (!data.chunk) return;
	streamingContent.value += data.chunk;

	if (data.task_type) remoteTaskType.value = data.task_type;
	if (data.block_id) remoteBlockId.value = data.block_id;

	throttledProcessModifyStreaming();
};

const onModifyComplete = (data: any) => {
	generating.value = false;
	applyTierLabel(data);
	// Wait for any remaining throttled updates to resolve
	setTimeout(() => {
		emit("modified");
	}, 300);
	prompt.value = "";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
};

const onModifyError = (data: any) => {
	generating.value = false;
	progressMessage.value = "";
	showDialog.value = true;
	errorMessage.value = data.message || "An error occurred while modifying the section";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
};

const eventName = (base: string) => (props.pageId ? `${base}_${props.pageId}` : base);

onMounted(() => {
	builderStore.realtime.on(eventName("ai_generation_progress"), onProgress);
	builderStore.realtime.on(eventName("ai_generation_stream"), onStream);
	builderStore.realtime.on(eventName("ai_generation_complete"), onComplete);
	builderStore.realtime.on(eventName("ai_generation_error"), onError);
	builderStore.realtime.on(eventName("ai_modify_progress"), onModifyProgress);
	builderStore.realtime.on(eventName("ai_modify_stream"), onModifyStream);
	builderStore.realtime.on(eventName("ai_modify_complete"), onModifyComplete);
	builderStore.realtime.on(eventName("ai_modify_error"), onModifyError);
});

onUnmounted(() => {
	builderStore.realtime.off(eventName("ai_generation_progress"), onProgress);
	builderStore.realtime.off(eventName("ai_generation_stream"), onStream);
	builderStore.realtime.off(eventName("ai_generation_complete"), onComplete);
	builderStore.realtime.off(eventName("ai_generation_error"), onError);
	builderStore.realtime.off(eventName("ai_modify_progress"), onModifyProgress);
	builderStore.realtime.off(eventName("ai_modify_stream"), onModifyStream);
	builderStore.realtime.off(eventName("ai_modify_complete"), onModifyComplete);
	builderStore.realtime.off(eventName("ai_modify_error"), onModifyError);
});

defineExpose({
	executeDirect,
});
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
