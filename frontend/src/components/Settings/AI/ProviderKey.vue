<template>
	<!-- how the provider signs in: its key, or a ChatGPT account -->
	<div class="flex flex-col gap-2">
		<span class="text-sm-medium text-ink-gray-6">
			{{ isChatGPT ? __("Account") : __("API Key") }}
		</span>
		<AddProvider
			v-if="isSigningIn"
			preset="codex"
			@close="isSigningIn = false"
			@connected="emit('changed')" />
		<div v-else-if="isChatGPT" class="flex items-center justify-between gap-3">
			<span class="text-p-sm text-ink-gray-7">{{ __("Signed in with ChatGPT") }}</span>
			<Button size="sm" :label="__('Sign In Again')" @click="isSigningIn = true" />
		</div>
		<span v-else-if="provider.from_site_config" class="text-p-sm text-ink-gray-7">
			{{ __("Set in the site config") }}
		</span>
		<form v-else class="flex gap-2" @submit.prevent="save">
			<FormControl
				v-model="newKey"
				class="flex-1"
				type="password"
				:placeholder="
					provider.api_key ? __('Paste a new key to replace the saved one') : __('Paste your API key')
				" />
			<Button type="submit" :label="__('Save')" :loading="isSaving" :disabled="!newKey" />
		</form>
	</div>
</template>

<script setup lang="ts">
import { api } from "@/components/ai/commands/shared";
import type { AISetupState } from "@/components/ai/types";
import AddProvider from "@/components/Settings/AI/AddProvider.vue";
import { saveProviderKey } from "@/data/aiModels";
import { __ } from "@/translation";
import type { BuilderAIProvider } from "@/types/doctypes";
import { Button, FormControl, toast } from "frappe-ui";
import { computed, ref } from "vue";

const props = defineProps<{ provider: BuilderAIProvider }>();
const emit = defineEmits<{ changed: [] }>();

const isChatGPT = computed(() => props.provider.litellm_provider === "codex");

const isSigningIn = ref(false);

const newKey = ref("");
const isSaving = ref(false);
/** a preset checks the key and its models as connecting does. An endpoint of your own only stores it */
const save = async () => {
	isSaving.value = true;
	try {
		const state = props.provider.api_base ? null : await api<AISetupState>("builder.ai.api.ai_setup_state");
		const preset = state?.presets.find((p) => p.name === props.provider.name);
		if (preset) await api("builder.ai.api.connect_ai_provider", { preset: preset.id, api_key: newKey.value });
		else await saveProviderKey(props.provider.name, newKey.value);
		newKey.value = "";
		toast.success(__("Key saved"));
		emit("changed");
	} finally {
		isSaving.value = false;
	}
};
</script>
