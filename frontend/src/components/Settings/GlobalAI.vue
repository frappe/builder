<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-2">
			<FormControl
				label="AI Provider"
				type="select"
				:options="providerOptions"
				:modelValue="builderSettings.doc?.ai_model"
				@update:modelValue="updateProvider" />
			<p class="text-xs text-ink-gray-6">AI provider for page generation</p>
		</div>
		<div class="flex flex-col gap-2">
			<label class="text-sm font-medium text-ink-gray-9">API Key</label>
			<div class="flex items-center gap-2">
				<FormControl
					type="password"
					:modelValue="apiKey"
					@update:modelValue="updateApiKey"
					placeholder="Enter API key for the selected provider"
					class="flex-1" />
				<Button v-if="apiKey" variant="subtle" @click="testApiKey" :disabled="testing">
					{{ testing ? "Testing..." : "Test Key" }}
				</Button>
			</div>
			<p class="text-xs text-ink-gray-6">API key for the selected provider. Stored in Builder Settings.</p>
		</div>
		<div v-if="statusMessage" class="rounded-lg p-3 text-sm" :class="statusClass">
			{{ statusMessage }}
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { createResource, FormControl } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

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

const builderStore = useBuilderStore();
const availableModels = ref<AIProvider[]>([]);
const testing = ref(false);
const statusMessage = ref("");
const statusClass = ref("");
const apiKey = ref("");

const providerOptions = computed(() => {
	const options: SelectOption[] = [{ label: "Select a provider...", value: "" }];
	availableModels.value.forEach((available) => {
		options.push({
			label: getProviderLabel(available.provider),
			value: available.provider,
		});
	});
	return options;
});

const getProviderLabel = (provider: string): string => {
	const labels: Record<string, string> = {
		openai: "OpenAI",
		anthropic: "Anthropic",
		google: "Google",
		"x-ai": "xAI",
		openrouter: "OpenRouter",
	};
	return labels[provider] || provider;
};

const updateProvider = (value: string) => {
	builderStore.updateBuilderSettings("ai_model", value);
};

const updateApiKey = (value: string) => {
	apiKey.value = value;
	builderStore.updateBuilderSettings("ai_api_key", value);
};

const testApiKey = async () => {
	const provider = builderSettings.doc?.ai_model;
	if (!apiKey.value || !provider) return;

	testing.value = true;
	statusMessage.value = "";

	try {
		const result = (await createResource({
			url: "builder.ai_page_generator.test_api_key",
			makeParams: () => ({
				model: provider,
				api_key: apiKey.value,
			}),
		}).submit()) as { success: boolean; message?: string };

		if (result.success) {
			statusMessage.value = "API key is valid!";
			statusClass.value = "text-ink-green-3 bg-surface-green-1";
		} else {
			statusMessage.value = result.message || "API key test failed";
			statusClass.value = "text-ink-red-3 bg-surface-red-1";
		}
	} catch (error: unknown) {
		statusMessage.value = error instanceof Error ? error.message : "Failed to test API key";
		statusClass.value = "text-ink-red-3 bg-surface-red-1";
	} finally {
		testing.value = false;
		setTimeout(() => {
			statusMessage.value = "";
		}, 5000);
	}
};

onMounted(() => {
	createResource({
		url: "builder.ai_page_generator.get_ai_models",
		auto: true,
		onSuccess: (data: AIProvider[]) => {
			availableModels.value = data;
		},
	});
	// Load the saved API key
	if (builderSettings.doc?.ai_api_key) {
		apiKey.value = builderSettings.doc.ai_api_key;
	}
});
</script>
