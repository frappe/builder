<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:title="isEdit ? provider.provider_name || 'Edit Provider' : 'New Provider'"
		size="lg"
		:actions="dialogActions">
		<template #default>
			<div class="flex flex-col gap-4">
				<div class="flex flex-col gap-1.5">
					<InputLabel>Name</InputLabel>
					<BuilderInput
						type="text"
						:autofocus="true"
						:modelValue="provider.provider_name"
						@update:modelValue="(value: string) => (provider.provider_name = value)"
						placeholder="Local Ollama"
						:hideClearButton="true" />
				</div>

				<div class="flex flex-col gap-1.5">
					<InputLabel>API Base</InputLabel>
					<BuilderInput
						type="text"
						:modelValue="provider.api_base"
						@update:modelValue="(value: string) => (provider.api_base = value)"
						placeholder="http://localhost:11434/v1"
						:hideClearButton="true" />
					<p class="text-p-xs text-ink-gray-5">Any OpenAI-compatible endpoint. Leave empty for OpenRouter.</p>
				</div>

				<div class="flex flex-col gap-1.5">
					<InputLabel>API Key</InputLabel>
					<div class="flex items-center gap-2">
						<BuilderInput
							type="password"
							class="flex-1"
							:modelValue="apiKey"
							@update:modelValue="(value: string) => (apiKey = value)"
							:placeholder="hasStoredKey ? 'Stored — type to replace' : 'sk-…'"
							:hideClearButton="true" />
						<Button v-if="isEdit" variant="subtle" :loading="testing" @click="test">Test</Button>
						<Button
							v-if="isEdit && provider.api_base"
							variant="subtle"
							:loading="importing"
							title="Ask this provider which models it serves"
							@click="importModels">
							Import models
						</Button>
					</div>
					<p v-if="testResult" class="text-p-xs" :class="testClass">{{ testResult }}</p>
					<p v-else class="text-p-xs text-ink-gray-5">
						Leave empty to use the OpenRouter key from Builder Settings.
					</p>
				</div>

				<label class="flex items-center gap-2 text-p-sm text-ink-gray-8">
					<Switch
						size="sm"
						:modelValue="Boolean(provider.enabled)"
						@update:modelValue="(value: boolean) => (provider.enabled = value ? 1 : 0)" />
					Enabled
					<span class="text-p-xs text-ink-gray-5">(off hides this provider's models)</span>
				</label>

				<details class="text-p-sm text-ink-gray-7">
					<summary class="cursor-pointer select-none text-ink-gray-6">Advanced</summary>
					<div class="mt-3 flex flex-col gap-4">
						<div class="grid grid-cols-2 gap-4">
							<div class="flex flex-col gap-1.5">
								<InputLabel>Route Prefix</InputLabel>
								<BuilderInput
									type="text"
									:modelValue="provider.route_prefix"
									@update:modelValue="(value: string) => (provider.route_prefix = value)"
									:placeholder="derivedPrefix"
									:hideClearButton="true" />
								<p class="text-p-xs text-ink-gray-5">Namespaces this provider's model names.</p>
							</div>
							<div class="flex flex-col gap-1.5">
								<InputLabel>LiteLLM Provider</InputLabel>
								<BuilderInput
									type="text"
									:modelValue="provider.litellm_provider"
									@update:modelValue="(value: string) => (provider.litellm_provider = value)"
									:placeholder="provider.api_base ? 'openai' : 'openrouter'"
									:hideClearButton="true" />
							</div>
						</div>
						<div class="grid grid-cols-2 gap-4">
							<div class="flex flex-col gap-1.5">
								<InputLabel>Extra Headers</InputLabel>
								<BuilderInput
									type="textarea"
									:modelValue="provider.extra_headers"
									@update:modelValue="(value: string) => (provider.extra_headers = value)"
									placeholder='{"User-Agent": "…"}'
									:hideClearButton="true" />
							</div>
							<div class="flex flex-col gap-1.5">
								<InputLabel>Extra Body</InputLabel>
								<BuilderInput
									type="textarea"
									:modelValue="provider.extra_body"
									@update:modelValue="(value: string) => (provider.extra_body = value)"
									placeholder='{"provider": {"order": ["anthropic"]}}'
									:hideClearButton="true" />
							</div>
						</div>
					</div>
				</details>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { defaultProvider } from "@/data/aiModels";
import { BuilderAIProvider } from "@/types/doctypes";
import { Button, createResource, Dialog, Switch, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps<{ modelValue: boolean; providerName?: string | null }>();
const emit = defineEmits(["update:modelValue", "saved"]);

const provider = ref<Partial<BuilderAIProvider>>(defaultProvider());
const apiKey = ref("");
const hasStoredKey = ref(false);
const testing = ref(false);
const importing = ref(false);
const testResult = ref("");
const testOk = ref(false);

const isEdit = computed(() => Boolean(props.providerName));
const testClass = computed(() => (testOk.value ? "text-ink-green-6" : "text-ink-red-6"));
const derivedPrefix = computed(() =>
	(provider.value.provider_name || "provider")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-|-$/g, ""),
);

const dialogActions = computed(() => [
	...(isEdit.value ? [{ label: "Delete", theme: "red" as const, onClick: remove }] : []),
	{ label: isEdit.value ? "Update" : "Create", variant: "solid" as const, onClick: save },
]);

watch(
	() => props.modelValue,
	async (open) => {
		if (!open) return;
		apiKey.value = "";
		testResult.value = "";
		if (!props.providerName) {
			provider.value = defaultProvider();
			hasStoredKey.value = false;
			return;
		}
		const doc = await createResource({ url: "frappe.client.get" }).submit({
			doctype: "Builder AI Provider",
			name: props.providerName,
		});
		provider.value = { ...doc };
		// Stored keys never come back to the client; an empty box means "keep it".
		hasStoredKey.value = Boolean(doc.api_key);
	},
);

const save = async () => {
	if (!provider.value.provider_name) {
		toast.error("Name is required");
		return;
	}
	try {
		await createResource({ url: "builder.ai.api.save_ai_provider" }).submit({
			provider: { ...provider.value, ...(apiKey.value ? { api_key: apiKey.value } : {}) },
			name: props.providerName || null,
		});
		toast.success(isEdit.value ? "Provider updated" : "Provider created");
		emit("saved");
		emit("update:modelValue", false);
	} catch (error) {
		toast.error((error as Error).message || "Could not save the provider");
	}
};

const test = async () => {
	testing.value = true;
	testResult.value = "";
	try {
		const result = (await createResource({ url: "builder.ai.api.test_api_key" }).submit({
			provider: props.providerName,
		})) as { success: boolean; message?: string };
		testOk.value = result.success;
		testResult.value = result.message || (result.success ? "Key works" : "Key failed");
	} catch (error) {
		testOk.value = false;
		testResult.value = (error as Error).message || "Could not reach the provider";
	} finally {
		testing.value = false;
	}
};

const importModels = async () => {
	importing.value = true;
	try {
		const result = (await createResource({ url: "builder.ai.api.import_provider_models" }).submit({
			provider: props.providerName,
		})) as { added: string[]; skipped: string[]; found: number };
		const parts = [`Added ${result.added.length} of ${result.found}`];
		// embeddings and rerankers answer /v1/models too; say so rather than silently dropping them
		if (result.skipped.length) parts.push(`skipped ${result.skipped.length} non-chat`);
		toast.success(parts.join(", "));
		emit("saved");
	} catch (error) {
		toast.error((error as Error).message || "Could not import models");
	} finally {
		importing.value = false;
	}
};

const remove = async () => {
	try {
		await createResource({ url: "frappe.client.delete" }).submit({
			doctype: "Builder AI Provider",
			name: props.providerName,
		});
		toast.success("Provider deleted");
		emit("saved");
		emit("update:modelValue", false);
	} catch (error) {
		toast.error((error as Error).message || "Could not delete the provider");
	}
};
</script>
