<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Generate with AI',
			size: 'lg',
		}">
		<template #body-content>
			<div class="flex flex-col gap-3">
				<textarea
					v-model="prompt"
					rows="4"
					class="focus:border-ink-blue-6 focus:ring-ink-blue-2 w-full rounded-md border border-outline-gray-3 p-3 text-sm focus:outline-none focus:ring-2"
					placeholder="Describe the section you want to create..."
					@keydown.meta.enter="generatePage"
					@keydown.ctrl.enter="generatePage"></textarea>

				<div v-if="errorMessage" class="text-ink-red-9 rounded-lg bg-surface-red-1 p-3 text-sm">
					{{ errorMessage }}
				</div>

				<p v-if="!hasAISettings" class="text-xs text-ink-gray-6">
					Configure your AI model and API key in
					<button @click="$emit('openSettings')" class="text-ink-blue-6 hover:underline">
						Settings &rarr; AI
					</button>
				</p>
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button variant="subtle" @click="showDialog = false">Cancel</Button>
				<Button
					variant="solid"
					@click="generatePage"
					:disabled="!canGenerate || generating"
					:loading="generating">
					{{ generating ? progressMessage || "Generating..." : "Generate" }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { createResource } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps<{
	modelValue: boolean;
}>();

const emit = defineEmits<{
	(e: "update:modelValue", value: boolean): void;
	(e: "generated", blocks: any[]): void;
	(e: "streaming", blocks: any[]): void;
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
 * Attempt to repair partial/incomplete JSON by closing open strings, arrays, and objects.
 * Returns a parseable JSON string or null if the content is too incomplete.
 */
function repairPartialJSON(partial: string): string | null {
	partial = partial.trim();
	if (!partial) return null;

	let result = partial;
	let inString = false;
	let escaped = false;
	const stack: string[] = [];

	for (let i = 0; i < result.length; i++) {
		const ch = result[i];
		if (escaped) {
			escaped = false;
			continue;
		}
		if (ch === "\\" && inString) {
			escaped = true;
			continue;
		}
		if (ch === '"') {
			inString = !inString;
			continue;
		}
		if (inString) continue;
		if (ch === "{" || ch === "[") stack.push(ch);
		else if (ch === "}") {
			if (stack.length && stack[stack.length - 1] === "{") stack.pop();
		} else if (ch === "]") {
			if (stack.length && stack[stack.length - 1] === "[") stack.pop();
		}
	}

	if (inString) {
		result += '"';
	}

	result = result.replace(/[,:\s]+$/, "");

	for (let i = stack.length - 1; i >= 0; i--) {
		result += stack[i] === "{" ? "}" : "]";
	}

	return result;
}

const canGenerate = computed(() => {
	return prompt.value.trim() !== "" && hasAISettings.value && !generating.value;
});

const generatePage = async () => {
	if (!canGenerate.value) return;

	generating.value = true;
	errorMessage.value = "";
	progressMessage.value = "Initializing...";
	streamingContent.value = "";

	showDialog.value = false;

	try {
		const result = await createResource({
			url: "builder.ai_page_generator.generate_page_from_prompt",
			makeParams: () => ({
				prompt: prompt.value,
			}),
		}).submit();

		if (result.success && result.blocks) {
			emit("generated", result.blocks);
			prompt.value = "";
		} else {
			showDialog.value = true;
			errorMessage.value = "Failed to generate page. Please try again.";
		}
	} catch (error: any) {
		showDialog.value = true;
		errorMessage.value = error.message || "An error occurred while generating the page";
	} finally {
		generating.value = false;
		progressMessage.value = "";
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
onMounted(() => {
	builderStore.realtime.on("ai_generation_progress", (data: any) => {
		if (data.message) {
			progressMessage.value = data.message;
		}
	});
	builderStore.realtime.on("ai_generation_stream", (data: any) => {
		if (data.chunk) {
			streamingContent.value += data.chunk;
			// Try to repair partial JSON and render live
			const repaired = repairPartialJSON(streamingContent.value);
			if (repaired) {
				try {
					let section = JSON.parse(repaired);
					if (Array.isArray(section)) section = section[0];
					if (section && typeof section === "object" && section.element) {
						const wrapped = [
							{
								element: "div",
								originalElement: "body",
								blockId: "root",
								children: [section],
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
					// Still not valid enough, wait for more chunks
				}
			}
		}
	});
});

onUnmounted(() => {
	builderStore.realtime.off("ai_generation_progress", () => {});
	builderStore.realtime.off("ai_generation_stream", () => {});
});
</script>
