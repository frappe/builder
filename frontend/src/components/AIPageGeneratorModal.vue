<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Generate Page with AI',
			size: '3xl',
		}">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<!-- Info Banner -->
				<div class="text-ink-blue-9 rounded-lg bg-surface-blue-1 p-3 text-sm">
					<div class="flex items-start gap-2">
						<FeatherIcon name="info" class="mt-0.5 h-4 w-4 flex-shrink-0" />
						<div>
							<p class="font-medium">Describe the page you want to create</p>
							<p class="text-ink-blue-8 mt-1 text-xs">
								The AI will generate a complete page structure with modern design. Be specific about the
								content, layout, and style you want.
							</p>
						</div>
					</div>
				</div>

				<!-- Prompt Input -->
				<div class="flex flex-col gap-2">
					<label class="text-sm font-medium text-ink-gray-9">Page Description</label>
					<textarea
						v-model="prompt"
						rows="6"
						class="focus:border-ink-blue-6 focus:ring-ink-blue-2 w-full rounded-md border border-outline-gray-3 p-3 text-sm focus:outline-none focus:ring-2"
						placeholder="Example: Create a modern landing page for a SaaS product with a hero section featuring a gradient background, a features section with 3 cards, testimonials, and a call-to-action section. Use a purple and blue color scheme."></textarea>
					<p class="text-xs text-ink-gray-6">Be specific about sections, colors, and content you want</p>
				</div>

				<!-- Model Selection -->
				<div class="flex flex-col gap-2">
					<label class="text-sm font-medium text-ink-gray-9">AI Model</label>
					<select
						v-model="selectedModel"
						class="focus:border-ink-blue-6 focus:ring-ink-blue-2 w-full rounded-md border border-outline-gray-3 p-2 text-sm focus:outline-none focus:ring-2">
						<option value="" disabled>Select a model...</option>
						<optgroup
							v-for="provider in availableModels"
							:key="provider.provider"
							:label="getProviderLabel(provider.provider)">
							<option v-for="model in provider.models" :key="model.name" :value="model.name">
								{{ model.label }}
							</option>
						</optgroup>
					</select>
				</div>

				<!-- API Key Input (conditional) -->
				<div v-if="showApiKeyInput" class="flex flex-col gap-2">
					<label class="flex items-center gap-2 text-sm font-medium text-ink-gray-9">
						API Key
						<button
							@click="testApiKey"
							:disabled="!tempApiKey || testing"
							class="text-ink-blue-6 hover:text-ink-blue-7 text-xs disabled:opacity-50">
							{{ testing ? "Testing..." : "Test Key" }}
						</button>
					</label>
					<input
						v-model="tempApiKey"
						type="password"
						class="focus:border-ink-blue-6 focus:ring-ink-blue-2 w-full rounded-md border border-outline-gray-3 p-2 text-sm focus:outline-none focus:ring-2"
						:placeholder="`Enter ${getProviderLabel(getProviderForModel(selectedModel))} API key`" />
					<p class="text-xs text-ink-gray-6">
						Your API key will be stored securely for this session. Configure permanent keys in site config.
					</p>
				</div>

				<!-- Examples -->
				<details class="text-sm">
					<summary class="cursor-pointer font-medium text-ink-gray-8 hover:text-ink-gray-9">
						View Example Prompts
					</summary>
					<div class="mt-2 space-y-2 rounded-lg bg-surface-gray-1 p-3">
						<button
							v-for="(example, index) in examplePrompts"
							:key="index"
							@click="prompt = example"
							class="block w-full rounded border border-outline-gray-3 p-2 text-left text-xs hover:bg-surface-gray-2">
							{{ example }}
						</button>
					</div>
				</details>

				<!-- Error Message -->
				<div v-if="errorMessage" class="text-ink-red-9 rounded-lg bg-surface-red-1 p-3 text-sm">
					<div class="flex items-start gap-2">
						<FeatherIcon name="alert-circle" class="mt-0.5 h-4 w-4 flex-shrink-0" />
						<div>
							<p class="font-medium">Error</p>
							<p class="mt-1 text-xs">{{ errorMessage }}</p>
						</div>
					</div>
				</div>

				<!-- Success Message -->
				<div v-if="successMessage" class="text-ink-green-9 rounded-lg bg-surface-green-1 p-3 text-sm">
					<div class="flex items-start gap-2">
						<FeatherIcon name="check-circle" class="mt-0.5 h-4 w-4 flex-shrink-0" />
						<div>
							<p class="font-medium">Success</p>
							<p class="mt-1 text-xs">{{ successMessage }}</p>
						</div>
					</div>
				</div>

				<!-- Progress Message -->
				<div
					v-if="progressMessage && generating"
					class="text-ink-blue-9 rounded-lg bg-surface-blue-1 p-3 text-sm">
					<div class="flex items-start gap-2">
						<span
							class="border-ink-blue-6 mt-0.5 inline-block h-4 w-4 animate-spin rounded-full border-2 border-t-transparent"></span>
						<div>
							<p class="font-medium">{{ progressMessage }}</p>
						</div>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-between">
				<button
					@click="showDialog = false"
					class="rounded-md px-4 py-2 text-sm font-medium text-ink-gray-8 hover:bg-surface-gray-2">
					Cancel
				</button>
				<Button
					@click="generatePage"
					:disabled="!canGenerate || generating"
					class="bg-ink-blue-2 hover:bg-ink-blue-7 rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50">
					<span v-if="generating" class="flex items-center gap-2">
						<span
							class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
						{{ progressMessage || "Generating..." }}
					</span>
					<span v-else>Generate Page</span>
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import useBuilderStore from "@/stores/builderStore";
import { createResource } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

declare global {
	interface Window {
		frappe?: {
			realtime?: {
				on: (event: string, callback: (data: any) => void) => void;
				off: (event: string) => void;
			};
		};
	}
}

const props = defineProps<{
	modelValue: boolean;
}>();

const emit = defineEmits<{
	(e: "update:modelValue", value: boolean): void;
	(e: "generated", blocks: any[]): void;
	(e: "streaming", blocks: any[]): void;
}>();

const showDialog = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const prompt = ref("");
const selectedModel = ref("");
const tempApiKey = ref("");
const generating = ref(false);
const testing = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const progressMessage = ref("");
const availableModels = ref<any[]>([]);
const showApiKeyInput = ref(true);
const streamingContent = ref("");
const builderStore = useBuilderStore();

/**
 * Attempt to repair partial/incomplete JSON by closing open strings, arrays, and objects.
 * Returns a parseable JSON string or null if the content is too incomplete.
 */
function repairPartialJSON(partial: string): string | null {
	partial = partial.trim();
	if (!partial) return null;

	// Remove trailing commas before we close things
	let result = partial;
	let inString = false;
	let escaped = false;
	const stack: string[] = []; // tracks open brackets: '{' or '['

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

	// If we're inside an unclosed string, close it
	if (inString) {
		result += '"';
	}

	// Remove any trailing comma or colon (invalid before closing)
	result = result.replace(/[,:\s]+$/, "");

	// Close any unclosed brackets/braces in reverse order
	for (let i = stack.length - 1; i >= 0; i--) {
		result += stack[i] === "{" ? "}" : "]";
	}

	return result;
}

const examplePrompts = [
	"Create a modern landing page for a fitness app with a hero section, features grid with icons, pricing table, and footer. Use energetic colors like orange and blue.",
	"Build a portfolio page for a photographer with a full-width image gallery, about section, and contact form. Use a dark theme with white text.",
	"Design a product showcase page for eco-friendly products with a navigation bar, hero banner, product cards in a grid, testimonials carousel, and newsletter signup. Use green and earth tones.",
	"Create a restaurant menu page with a header, category sections (appetizers, mains, desserts), food cards with images and prices, and contact information. Use warm colors.",
	"Build a team/about us page with individual team member cards showing photos, names, roles, and social links. Use a professional blue color scheme.",
];

// Load available models
const modelsResource = createResource({
	url: "builder.ai_page_generator.get_ai_models",
	auto: true,
	onSuccess: (data: any) => {
		availableModels.value = data;
		// Select first available model by default
		if (data && data.length > 0 && data[0].models && data[0].models.length > 0) {
			selectedModel.value = data[0].models[0].name;
		}
	},
});

const canGenerate = computed(() => {
	return prompt.value.trim() !== "" && selectedModel.value !== "" && !generating.value;
});

const getProviderLabel = (provider: string): string => {
	const labels: Record<string, string> = {
		openai: "OpenAI",
		anthropic: "Anthropic",
		google: "Google",
		"x-ai": "xAI",
	};
	return labels[provider] || provider;
};

const getProviderForModel = (model: string): string => {
	if (
		model.startsWith("gpt-") ||
		model.startsWith("chatgpt-") ||
		model.startsWith("o1") ||
		model.startsWith("o3")
	)
		return "openai";
	if (model.startsWith("claude-")) return "anthropic";
	if (model.startsWith("gemini-")) return "google";
	if (model.startsWith("grok-")) return "x-ai";
	return "openai";
};

const testApiKey = async () => {
	if (!tempApiKey.value || !selectedModel.value) return;

	testing.value = true;
	errorMessage.value = "";
	successMessage.value = "";

	try {
		const result = await createResource({
			url: "builder.ai_page_generator.test_api_key",
			makeParams: () => ({
				model: selectedModel.value,
				api_key: tempApiKey.value,
			}),
		}).submit();

		if (result.success) {
			successMessage.value = "API key is valid!";
			setTimeout(() => {
				successMessage.value = "";
			}, 3000);
		} else {
			errorMessage.value = result.message || "API key test failed";
		}
	} catch (error: any) {
		errorMessage.value = error.message || "Failed to test API key";
	} finally {
		testing.value = false;
	}
};

const generatePage = async () => {
	if (!canGenerate.value) return;

	generating.value = true;
	errorMessage.value = "";
	successMessage.value = "";
	progressMessage.value = "Initializing...";
	streamingContent.value = "";

	// Close dialog immediately so user sees blocks render live on canvas
	showDialog.value = false;

	try {
		const result = await createResource({
			url: "builder.ai_page_generator.generate_page_from_prompt",
			makeParams: () => ({
				prompt: prompt.value,
				model: selectedModel.value,
				api_key: tempApiKey.value || null,
			}),
		}).submit();

		if (result.success && result.blocks) {
			// Emit final blocks (properly parsed by the server)
			emit("generated", result.blocks);
			prompt.value = "";
			tempApiKey.value = "";
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

// Watch for model changes to update API key input visibility
watch(selectedModel, () => {
	errorMessage.value = "";
	successMessage.value = "";
});

// Reset messages when dialog is opened/closed
watch(showDialog, (newValue) => {
	if (newValue) {
		errorMessage.value = "";
		successMessage.value = "";
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
