<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		:title="isEdit ? provider.provider_name || 'Edit Provider' : 'New Provider'"
		size="lg">
		<template #actions>
			<div class="flex items-center justify-between">
				<Button v-if="isEdit" variant="ghost" theme="red" class="!text-ink-red-8" @click="remove">
					Delete
				</Button>
				<span v-else />
				<Button variant="solid" @click="save">{{ isEdit ? "Update" : "Create" }}</Button>
			</div>
		</template>
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
							placeholder="sk-…"
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
						{{
							hasStoredKey
								? "Type over it to replace, or clear it to remove the key."
								: "Leave empty to fall back to the OpenRouter key in Builder Settings."
						}}
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

/** The framework's dummy password: all asterisks, meaning "unchanged". Mirrors
 * base_document.is_dummy_password so an untouched field is never saved back as
 * the literal asterisks. */
const isDummyKey = (value?: string) => !!value && /^\*+$/.test(value);

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
		// A Password field comes back as the framework's dummy — one '*' per
		// character of the real key, never the key itself (base_document
		// _save_passwords). Showing it is what Desk does, and it reads as "something
		// is set here" far better than a placeholder does.
		apiKey.value = doc.api_key || "";
		hasStoredKey.value = isDummyKey(doc.api_key);
	},
);

const save = async () => {
	if (!provider.value.provider_name) {
		toast.error("Name is required");
		return;
	}
	try {
		await createResource({ url: "builder.ai.api.save_ai_provider" }).submit({
			provider: {
				...provider.value,
				...(apiKey.value && !isDummyKey(apiKey.value) ? { api_key: apiKey.value } : {}),
			},
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
		// The server's reason is in `messages` / `exc`; the Error's own message is
		// just the class name, so deleting a provider that still has models used to
		// surface as a bare "ValidationError".
		toast.error(serverMessage(error) || "Could not delete the provider");
	}
};

function serverMessage(error: unknown): string {
	const e = error as { messages?: string[]; exc?: string; message?: string };
	const raw = e?.messages?.[0] || e?.exc?.split("\n").filter(Boolean).slice(-1)[0] || e?.message || "";
	// Server messages can carry markup (doc links) — show the text.
	return raw.replace(/<[^>]+>/g, "").trim();
}
</script>
