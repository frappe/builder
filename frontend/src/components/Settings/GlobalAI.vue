<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-2">
			<FormControl
				label="AI Model"
				type="select"
				:options="flattenedModels"
				:modelValue="builderSettings.doc?.ai_model"
				@update:modelValue="updateModel" />
			<p class="text-xs text-ink-gray-6">Model used for AI page generation</p>
		</div>
		<div class="flex flex-col gap-2">
			<FormControl
				type="password"
				:modelValue="apiKey"
				@update:modelValue="updateApiKey"
				placeholder="Enter API key for the selected provider">
				<template #label>
					<label class="flex items-center gap-2 text-sm font-medium text-ink-gray-9">
						API Key
						<button
							v-if="apiKey"
							@click="testApiKey"
							:disabled="testing"
							class="text-ink-blue-6 hover:text-ink-blue-7 text-xs disabled:opacity-50">
							{{ testing ? "Testing..." : "Test Key" }}
						</button>
					</label>
				</template>
			</FormControl>
			<p class="text-xs text-ink-gray-6">
				API key for the selected model's provider. Stored in Builder Settings.
			</p>
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

const builderStore = useBuilderStore();
const availableModels = ref<any[]>([]);
const testing = ref(false);
const statusMessage = ref("");
const statusClass = ref("");
const apiKey = ref("");

const flattenedModels = computed(() => {
	const options: any[] = [{ label: "Select a model...", value: "" }];
	availableModels.value.forEach((provider) => {
		provider.models.forEach((model: any) => {
			options.push({
				label: `${getProviderLabel(provider.provider)}: ${model.label}`,
				value: model.name,
			});
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
	};
	return labels[provider] || provider;
};

const updateModel = (value: string) => {
	builderStore.updateBuilderSettings("ai_model", value);
};

const updateApiKey = (value: string) => {
	apiKey.value = value;
	builderStore.updateBuilderSettings("ai_api_key", value);
};

const testApiKey = async () => {
	const model = builderSettings.doc?.ai_model;
	if (!apiKey.value || !model) return;

	testing.value = true;
	statusMessage.value = "";

	try {
		const result = await createResource({
			url: "builder.ai_page_generator.test_api_key",
			makeParams: () => ({
				model: model,
				api_key: apiKey.value,
			}),
		}).submit();

		if (result.success) {
			statusMessage.value = "API key is valid!";
			statusClass.value = "text-ink-green-3 bg-surface-green-1";
		} else {
			statusMessage.value = result.message || "API key test failed";
			statusClass.value = "text-ink-red-3 bg-surface-red-1";
		}
	} catch (error: any) {
		statusMessage.value = error.message || "Failed to test API key";
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
		onSuccess: (data: any) => {
			availableModels.value = data;
		},
	});
	// Load the saved API key
	if (builderSettings.doc?.ai_api_key) {
		apiKey.value = builderSettings.doc.ai_api_key;
	}
});
</script>
