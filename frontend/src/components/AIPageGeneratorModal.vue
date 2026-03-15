<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: mode === 'modify' ? 'Modify with AI' : 'Generate with AI',
			size: 'lg',
		}">
		<template #body-content>
			<div class="flex flex-col gap-3">
				<Textarea
					v-model="prompt"
					:rows="4"
					variant="outline"
					:placeholder="
						mode === 'modify'
							? 'Describe how you want to modify this section...'
							: 'Describe the section you want to create...'
					"
					@keydown.meta.enter="handleSubmit"
					@keydown.ctrl.enter="handleSubmit" />

				<div v-if="errorMessage" class="text-ink-red-9 rounded-lg bg-surface-red-1 p-3 text-sm">
					{{ errorMessage }}
				</div>

				<p v-if="!hasAISettings" class="text-xs text-ink-gray-6">
					Configure your AI model and API key in
					<Button variant="link" @click="$emit('openSettings')">Settings &rarr; AI</Button>
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button variant="subtle" @click="showDialog = false">Cancel</Button>
				<Button
					variant="solid"
					@click="handleSubmit"
					:disabled="!canGenerate || generating">
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
					<FeatherIcon
						v-if="generating"
						name="loader"
						class="h-4 w-4 animate-spin text-ink-gray-7" />
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
import Dialog from "@/components/Controls/Dialog.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { createResource, FeatherIcon, Textarea } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import yaml from "js-yaml";

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
	(e: "generated", blocks: any[]): void;
	(e: "streaming", blocks: any[]): void;
	(e: "modified", blocks: any[]): void;
	(e: "modifyStreaming", blocks: any[]): void;
	(e: "openSettings"): void;
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
const builderStore = useBuilderStore();

const hasAISettings = computed(() => {
	return builderSettings.doc?.ai_model && builderSettings.doc?.ai_api_key;
});

/**
 * Attempt to parse incomplete YAML stream content.
 * Returns a JS object or null if too incomplete.
 */
function expandDSL(dslBlock: any): any {
	if (!dslBlock || typeof dslBlock !== "object" || Array.isArray(dslBlock)) return dslBlock;

	const ensureObj = (val: any) => (val && typeof val === "object" && !Array.isArray(val) ? val : {});
	const ensureArray = (val: any) => (Array.isArray(val) ? val : []);

	const block: any = {
		element: dslBlock.el || "div",
		blockName: dslBlock.name || "",
		baseStyles: ensureObj(dslBlock.style),
		attributes: ensureObj(dslBlock.attrs),
		mobileStyles: ensureObj(dslBlock.m_style),
		tabletStyles: ensureObj(dslBlock.t_style),
		classes: ensureArray(dslBlock.classes),
	};
	if (dslBlock.id) block.blockId = dslBlock.id;
	if (dslBlock.text) block.innerText = dslBlock.text;

	if (Array.isArray(dslBlock.c)) {
		block.children = dslBlock.c.map(expandDSL);
	} else {
		block.children = [];
	}
	return block;
}

function getValidPartialYAML(yamlStr: string): any {
	let cleaned = yamlStr.trim();
	if (cleaned.startsWith("```")) {
		const lines = cleaned.split("\n");
		if (lines.length > 0) lines.shift(); // remove ```yaml or ```
		if (lines.length > 0 && lines[lines.length - 1].startsWith("```")) {
			lines.pop();
		}
		cleaned = lines.join("\n");
	}

	try {
		return yaml.load(cleaned);
	} catch (e) {
		const lines = cleaned.split("\n");
		for (let i = lines.length - 1; i > 0; i--) {
			try {
				const slice = lines.slice(0, i).join("\n");
				const parsed = yaml.load(slice);
				if (parsed) return parsed;
			} catch (err) {}
		}
	}
	return null;
}

const canGenerate = computed(() => {
	return prompt.value.trim() !== "" && hasAISettings.value && !generating.value;
});

const handleSubmit = async () => {
	if (props.mode === "modify") {
		await modifySection();
	} else {
		await generatePage();
	}
};

const generatePage = async () => {
	if (!canGenerate.value) return;

	generating.value = true;
	errorMessage.value = "";
	progressMessage.value = "Initializing...";
	streamingContent.value = "";

	showDialog.value = false;

	try {
		// Fire and forget — results come through realtime events
		await createResource({
			url: "builder.ai_page_generator.generate_page_from_prompt",
			makeParams: () => ({
				prompt: prompt.value,
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
				prompt: prompt.value,
				block_context: JSON.stringify(props.blockContext),
				page_id: props.pageId,
			}),
		}).submit();
	} catch (error: any) {
		generating.value = false;
		progressMessage.value = "";
		showDialog.value = true;
		errorMessage.value = error.message || "An error occurred while modifying the section";
	}
};

watch(showDialog, (newValue) => {
	if (newValue) {
		errorMessage.value = "";
		progressMessage.value = "";
		streamingContent.value = "";
	}
});

// Setup socket connection for progress updates
const onProgress = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	if (data.message) {
		progressMessage.value = data.message;
	}
};

const onStream = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	if (data.chunk) {
		streamingContent.value += data.chunk;
		const parsed = getValidPartialYAML(streamingContent.value);
		if (parsed) {
			try {
				let parsedArray = Array.isArray(parsed) ? parsed : [parsed];
				let sections = parsedArray.filter((s: any) => s && typeof s === "object" && s.el);
				sections = sections.map(expandDSL);
				if (sections.length > 0) {
					const wrapped = [
						{
							element: "div",
							originalElement: "body",
							blockId: "root",
							children: sections,
							baseStyles: {
								display: "flex",
								flexWrap: "wrap",
								flexShrink: "0",
								flexDirection: "column",
								alignItems: "center",
							},
							attributes: {},
							mobileStyles: {},
							tabletStyles: {},
						},
					];
					emit("streaming", wrapped);
				}
			} catch {
				// Ignore errors in partial parse
			}
		}
	}
};

const onComplete = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	generating.value = false;
	if (data.model_used) {
		const tierLabels: Record<string, string> = {
			trivial: "quick",
			simple: "fast",
			moderate: "standard",
			complex: "full",
		};
		const tierLabel = tierLabels[data.task_tier as string] || "";
		progressMessage.value = `Done — ${tierLabel} mode with ${data.model_used}`;
		setTimeout(() => {
			progressMessage.value = "";
		}, 2000);
	} else {
		progressMessage.value = "";
	}
	if (data.blocks) {
		emit("generated", data.blocks);
		prompt.value = "";
	}
};

const onError = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	generating.value = false;
	progressMessage.value = "";
	showDialog.value = true;
	errorMessage.value = data.message || "An error occurred while generating the page";
};

// Modify mode realtime event handlers
const onModifyProgress = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	if (data.message) {
		progressMessage.value = data.message;
	}
};

const onModifyStream = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	if (data.chunk) {
		streamingContent.value += data.chunk;
		const parsed = getValidPartialYAML(streamingContent.value);
		if (parsed) {
			try {
				let parsedArray = Array.isArray(parsed) ? parsed : [parsed];
				let sections = parsedArray.filter((s: any) => s && typeof s === "object" && s.el);
				sections = sections.map(expandDSL);
				if (sections.length > 0) {
					emit("modifyStreaming", sections);
				}
			} catch {
				// Ignore
			}
		}
	}
};

const onModifyComplete = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	generating.value = false;
	if (data.model_used) {
		const tierLabels: Record<string, string> = {
			trivial: "quick",
			simple: "fast",
			moderate: "standard",
			complex: "full",
		};
		const tierLabel = tierLabels[data.task_tier as string] || "";
		progressMessage.value = `Done — ${tierLabel} mode with ${data.model_used}`;
		setTimeout(() => {
			progressMessage.value = "";
		}, 2000);
	} else {
		progressMessage.value = "";
	}
	if (data.blocks) {
		emit("modified", data.blocks);
		prompt.value = "";
	}
};

const onModifyError = (data: any) => {
	if (data.page_id && data.page_id !== props.pageId) return;
	generating.value = false;
	progressMessage.value = "";
	showDialog.value = true;
	errorMessage.value = data.message || "An error occurred while modifying the section";
};

onMounted(() => {
	builderStore.realtime.on("ai_generation_progress", onProgress);
	builderStore.realtime.on("ai_generation_stream", onStream);
	builderStore.realtime.on("ai_generation_complete", onComplete);
	builderStore.realtime.on("ai_generation_error", onError);
	builderStore.realtime.on("ai_modify_progress", onModifyProgress);
	builderStore.realtime.on("ai_modify_stream", onModifyStream);
	builderStore.realtime.on("ai_modify_complete", onModifyComplete);
	builderStore.realtime.on("ai_modify_error", onModifyError);
});

onUnmounted(() => {
	builderStore.realtime.off("ai_generation_progress", onProgress);
	builderStore.realtime.off("ai_generation_stream", onStream);
	builderStore.realtime.off("ai_generation_complete", onComplete);
	builderStore.realtime.off("ai_generation_error", onError);
	builderStore.realtime.off("ai_modify_progress", onModifyProgress);
	builderStore.realtime.off("ai_modify_stream", onModifyStream);
	builderStore.realtime.off("ai_modify_complete", onModifyComplete);
	builderStore.realtime.off("ai_modify_error", onModifyError);
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
