<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-2">
			<label class="text-sm text-ink-gray-9">AI Provider</label>
			<Select
				:modelValue="provider"
				@update:modelValue="updateProvider"
				:options="providerOptions" />
		</div>

		<div class="flex flex-col gap-2">
			<label class="text-sm text-ink-gray-9">
				{{ provider === "openai_compatible" ? "API Key" : "OpenRouter API Key" }}
			</label>
			<div class="flex items-center gap-2">
				<FormControl
					type="password"
					:modelValue="apiKey"
					@update:modelValue="updateApiKey"
					:placeholder="provider === 'openai_compatible' ? 'sk-...' : 'sk-or-v1-…'"
					class="flex-1" />
				<Button v-if="apiKey" variant="subtle" @click="testApiKey" :disabled="testing">
					{{ testing ? "测试中..." : "测试密钥" }}
				</Button>
			</div>
			<p v-if="provider !== 'openai_compatible'" class="text-xs text-ink-gray-6">
				从
				<a
					href="https://openrouter.ai/keys"
					target="_blank"
					rel="noopener noreferrer"
					class="text-ink-blue-8 underline">
					openrouter.ai/keys
				</a>
				获取 API key —— 一个 key 支持 Claude、Gemini、GPT 等。
			</p>
		</div>

		<template v-if="provider === 'openai_compatible'">
			<div class="flex flex-col gap-2">
				<label class="text-sm text-ink-gray-9">API Base URL</label>
				<FormControl
					:modelValue="apiBase"
					@update:modelValue="updateApiBase"
					placeholder="https://api.openai.com/v1" />
				<p class="text-xs text-ink-gray-6">
					OpenAI 兼容服务的 API 地址（如 DeepSeek、通义千问、智谱 GLM、本地 vLLM）。
				</p>
			</div>
			<div class="flex flex-col gap-2">
				<label class="text-sm text-ink-gray-9">模型名称</label>
				<FormControl
					:modelValue="modelName"
					@update:modelValue="updateModelName"
					placeholder="gpt-4o / deepseek-chat" />
				<p class="text-xs text-ink-gray-6">对应服务支持的模型名（必填）。</p>
			</div>
		</template>

		<div v-if="statusMessage" class="rounded-lg p-3 text-sm" :class="statusClass">
			{{ statusMessage }}
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { Button, createResource, FormControl, Select } from "frappe-ui";
import { onMounted, ref } from "vue";

const builderStore = useBuilderStore();

const testing = ref(false);
const statusMessage = ref("");
const statusClass = ref("");
const provider = ref("openrouter");
const apiKey = ref("");
const apiBase = ref("");
const modelName = ref("");

const providerOptions = [
	{ label: "OpenRouter", value: "openrouter" },
	{ label: "OpenAI 兼容", value: "openai_compatible" },
];

const updateProvider = (value: string) => {
	provider.value = value;
	builderStore.updateBuilderSettings("ai_provider", value);
};

const updateApiKey = (value: string) => {
	apiKey.value = value;
	builderStore.updateBuilderSettings("ai_api_key", value);
};

const updateApiBase = (value: string) => {
	apiBase.value = value;
	builderStore.updateBuilderSettings("ai_api_base", value);
};

const updateModelName = (value: string) => {
	modelName.value = value;
	builderStore.updateBuilderSettings("ai_model", value);
};

const testApiKey = async () => {
	if (!apiKey.value) return;

	testing.value = true;
	statusMessage.value = "";

	try {
		const result = (await createResource({
			url: "builder.ai_page_generator.test_api_key",
		}).submit()) as { success: boolean; message?: string };

		if (result.success) {
			statusMessage.value = "API key 有效！";
			statusClass.value = "text-ink-green-6 bg-surface-green-1";
		} else {
			statusMessage.value = result.message || "API key 测试失败";
			statusClass.value = "text-ink-red-6 bg-surface-red-1";
		}
	} catch (error: unknown) {
		statusMessage.value = error instanceof Error ? error.message : "测试 API key 失败";
		statusClass.value = "text-ink-red-6 bg-surface-red-1";
	} finally {
		testing.value = false;
		setTimeout(() => {
			statusMessage.value = "";
		}, 5000);
	}
};

onMounted(() => {
	const doc = builderSettings.doc;
	if (!doc) return;
	if (doc.ai_provider) provider.value = doc.ai_provider;
	if (doc.ai_api_key) apiKey.value = doc.ai_api_key;
	if (doc.ai_api_base) apiBase.value = doc.ai_api_base;
	if (doc.ai_model) modelName.value = doc.ai_model;
});
</script>
