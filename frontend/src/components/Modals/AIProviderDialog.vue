<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:title="isEdit ? provider.provider_name || 'Edit Provider' : 'New Provider'"
		size="xl"
		:actions="[{ label: isEdit ? 'Update' : 'Create', variant: 'solid', onClick: save }]">
		<template #default>
			<div class="flex flex-col gap-4">
				<div class="grid grid-cols-2 gap-4">
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
						<InputLabel>Route Prefix</InputLabel>
						<BuilderInput
							type="text"
							:modelValue="provider.route_prefix"
							@update:modelValue="(value: string) => (provider.route_prefix = value)"
							placeholder="ollama-local"
							:hideClearButton="true" />
						<p class="text-p-xs text-ink-gray-5">Namespaces this provider's model names.</p>
					</div>
				</div>
				<div class="grid grid-cols-2 gap-4">
					<div class="flex flex-col gap-1.5">
						<InputLabel>LiteLLM Provider</InputLabel>
						<Autocomplete
							:options="LITELLM_PROVIDERS"
							:modelValue="provider.litellm_provider"
							@update:modelValue="(value: string | null) => (provider.litellm_provider = value || '')"
							placeholder="openai" />
						<p class="text-p-xs text-ink-gray-5">Use openai for any OpenAI-compatible endpoint.</p>
					</div>
					<div class="flex flex-col gap-1.5">
						<InputLabel>API Base</InputLabel>
						<BuilderInput
							type="text"
							:modelValue="provider.api_base"
							@update:modelValue="(value: string) => (provider.api_base = value)"
							placeholder="http://localhost:11434/v1"
							:hideClearButton="true" />
						<p class="text-p-xs text-ink-gray-5">Leave empty for OpenRouter.</p>
					</div>
				</div>

				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between">
						<InputLabel>API Keys</InputLabel>
						<Button size="sm" variant="ghost" iconLeft="lucide-plus" @click="addKey">Add key</Button>
					</div>
					<p v-if="!keys.length" class="text-p-xs text-ink-gray-5">
						No keys: this provider uses the OpenRouter key from Settings.
					</p>
					<div
						v-for="(key, index) in keys"
						:key="index"
						class="flex items-center gap-2 rounded border border-outline-gray-1 p-2">
						<BuilderInput
							type="text"
							class="w-32"
							:modelValue="key.key_name"
							@update:modelValue="(value: string) => (key.key_name = value)"
							placeholder="personal"
							:hideClearButton="true" />
						<BuilderInput
							type="password"
							class="flex-1"
							:modelValue="key.api_key"
							@update:modelValue="(value: string) => (key.api_key = value)"
							:placeholder="key.__saved ? 'Stored — type to replace' : 'sk-…'"
							:hideClearButton="true" />
						<Button
							:variant="key.is_active ? 'solid' : 'subtle'"
							size="sm"
							:title="key.is_active ? 'In use' : 'Use this key'"
							@click="activate(index)">
							{{ key.is_active ? "Active" : "Use" }}
						</Button>
						<Button variant="ghost" size="sm" icon="lucide-trash-2" @click="keys.splice(index, 1)" />
					</div>
				</div>

				<details class="text-p-sm text-ink-gray-7">
					<summary class="cursor-pointer select-none">Advanced</summary>
					<div class="mt-3 grid grid-cols-2 gap-4">
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
				</details>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import { defaultProvider } from "@/data/aiModels";
import { BuilderAIProvider } from "@/types/doctypes";
import { Button, createResource, Dialog, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

type ProviderKey = { key_name: string; api_key: string; is_active: 0 | 1; __saved?: boolean };

const props = defineProps<{ modelValue: boolean; providerName?: string | null }>();
const emit = defineEmits(["update:modelValue", "saved"]);

const LITELLM_PROVIDERS = [
	{ label: "openai (any OpenAI-compatible endpoint)", value: "openai" },
	{ label: "openrouter", value: "openrouter" },
	{ label: "anthropic", value: "anthropic" },
	{ label: "gemini", value: "gemini" },
	{ label: "ollama", value: "ollama" },
];

const provider = ref<Partial<BuilderAIProvider>>(defaultProvider());
const keys = ref<ProviderKey[]>([]);
const isEdit = computed(() => Boolean(props.providerName));

watch(
	() => props.modelValue,
	async (open) => {
		if (!open) return;
		keys.value = [];
		if (!props.providerName) {
			provider.value = defaultProvider();
			return;
		}
		const doc = await createResource({ url: "frappe.client.get" }).submit({
			doctype: "Builder AI Provider",
			name: props.providerName,
		});
		provider.value = { ...doc };
		// Stored keys come back masked; an untouched value means "keep it".
		keys.value = (doc.keys || []).map((row: any) => ({
			key_name: row.key_name,
			api_key: "",
			is_active: row.is_active,
			__saved: true,
		}));
	},
);

const addKey = () => {
	keys.value.push({ key_name: "", api_key: "", is_active: keys.value.length ? 0 : 1 });
};

const activate = (index: number) => {
	keys.value.forEach((key, i) => (key.is_active = i === index ? 1 : 0));
};

const save = async () => {
	if (!provider.value.provider_name || !provider.value.route_prefix) {
		toast.error("Name and route prefix are required");
		return;
	}
	if (keys.value.some((key) => !key.key_name || (!key.api_key && !key.__saved))) {
		toast.error("Every key needs a name and a value");
		return;
	}
	const payload = {
		...provider.value,
		keys: keys.value.map((key) => ({
			key_name: key.key_name,
			is_active: key.is_active,
			// omitted on purpose when untouched: the server keeps the stored key
			...(key.api_key ? { api_key: key.api_key } : {}),
		})),
	};
	try {
		await createResource({ url: "builder.ai.api.save_ai_provider" }).submit({
			provider: payload,
			name: props.providerName || null,
		});
		toast.success(isEdit.value ? "Provider updated" : "Provider created");
		emit("saved");
		emit("update:modelValue", false);
	} catch (error) {
		toast.error((error as Error).message || "Could not save the provider");
	}
};
</script>
