<template>
	<!-- adding a provider happens in one full-width row: each step swaps what the row holds, at one height -->
	<div ref="root" class="flex flex-col gap-1.5">
		<div class="flex items-center gap-2">
			<Button
				v-if="step === 'start'"
				class="w-full"
				icon-left="lucide-plus"
				:label="__('Add a Provider')"
				@click="pick" />

			<template v-else-if="step === 'pick'">
				<!-- Enter picks while the list is open, and continues once a provider is chosen -->
				<div class="flex-1" @keydown.enter.capture="continueOnEnter">
					<Combobox
						ref="picker"
						v-model:open="isPickerOpen"
						class="w-full"
						:placeholder="__('Search providers')"
						:options="presetOptions"
						:model-value="chosen?.id ?? null"
						@update:model-value="(id: unknown) => (chosen = presets.find((p) => p.id === id) ?? null)" />
				</div>
				<Button variant="solid" :label="__('Continue')" :disabled="!chosen" @click="next" />
			</template>

			<form v-else-if="step === 'url'" class="flex flex-1 items-center gap-2" @submit.prevent="next">
				<FormControl
					v-model="url"
					class="flex-1"
					:placeholder="__('Base URL, like http://localhost:11434/v1')" />
				<Button type="submit" variant="solid" :label="__('Continue')" :disabled="!url" />
			</form>

			<form v-else-if="step === 'key'" class="flex flex-1 items-center gap-2" @submit.prevent="connect">
				<FormControl v-model="apiKey" class="flex-1" type="password" :placeholder="keyPlaceholder" />
				<Button
					v-if="keyHost"
					icon="lucide-external-link"
					:tooltip="__('Get a key at {0}', [keyHost])"
					:aria-label="__('Get a key at {0}', [keyHost])"
					@click="openKeyPage" />
				<Button type="submit" variant="solid" :label="__('Save')" :loading="isConnecting" />
			</form>

			<template v-else-if="step === 'device'">
				<div class="flex h-7 flex-1 items-center rounded-4 bg-surface-gray-2 px-2">
					<LoadingIndicator v-if="!signIn" class="size-4 text-ink-gray-4" />
					<code v-else class="font-mono text-base tracking-widest text-ink-gray-9">{{ signIn.code }}</code>
				</div>
				<Button
					icon-left="lucide-copy"
					:label="__('Copy and Open ChatGPT')"
					:disabled="!signIn"
					@click="copyAndOpen" />
			</template>

			<Button
				v-if="step !== 'start'"
				variant="ghost"
				icon="lucide-x"
				:tooltip="__('Cancel')"
				:aria-label="__('Cancel')"
				@click="cancel" />
		</div>
		<p v-if="note" class="text-p-sm text-ink-gray-5">{{ note }}</p>
		<ErrorMessage :message="error" />
	</div>
</template>

<script setup lang="ts">
import { connected, connectEndpoint, pollDeviceSignIn } from "@/components/ai/commands/connect";
import { api } from "@/components/ai/commands/shared";
import type { AIPreset, AISetupState, ConnectResult, DeviceSignIn } from "@/components/ai/types";
import { reloadAIRegistry, selectedAIModel } from "@/data/aiModels";
import { __ } from "@/translation";
import { getErrorMessage } from "@/utils/helpers";
import { Button, Combobox, ErrorMessage, FormControl, LoadingIndicator } from "frappe-ui";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

type Step = "start" | "pick" | "url" | "key" | "device";

/** `preset` starts straight on that provider's step, as signing in to ChatGPT again does. Cancel then closes */
const props = defineProps<{ preset?: string }>();
const emit = defineEmits<{ connected: []; close: [] }>();

// connecting switches Bob to the provider's best model. The list reloads the rest once told
const setup = { chat: { selectedModel: selectedAIModel }, refreshAI: reloadAIRegistry };

const step = ref<Step>("start");
const presets = ref<AIPreset[]>([]);
const chosen = ref<AIPreset | null>(null);
const isPickerOpen = ref(false);
const picker = ref<{ focus: () => void } | null>(null);
const root = ref<HTMLElement | null>(null);
const url = ref("");
const apiKey = ref("");
const error = ref("");
const isConnecting = ref(false);
const signIn = ref<DeviceSignIn | null>(null);
const signInNote = ref("");
let stopSignIn = () => {};

const loadPresets = async () => {
	presets.value = (await api<AISetupState>("builder.ai.api.ai_setup_state")).presets;
};
onMounted(async () => {
	if (!props.preset) return;
	await loadPresets();
	chosen.value = presets.value.find((p) => p.id === props.preset) ?? null;
	next();
});
onBeforeUnmount(() => stopSignIn());

// searchable by name, with each provider's tagline under it
const presetOptions = computed(() =>
	presets.value.map((p) => ({
		label: p.name || __("Other Endpoint"),
		value: p.id,
		description: p.connected ? `${__("Connected")} · ${p.tagline}` : p.tagline,
	})),
);
const keyHost = computed(() => (chosen.value?.key_url ? new URL(chosen.value.key_url).host : ""));
const keyPlaceholder = computed(() => {
	if (chosen.value?.custom) return __("API key, or leave it empty if the endpoint needs none");
	const name = chosen.value?.name ?? "";
	return chosen.value?.key_prefix
		? __("Paste your {0} API key ({1}…)", [name, chosen.value.key_prefix])
		: __("Paste your {0} API key", [name]);
});
const note = computed(() => {
	if (step.value === "device") return signInNote.value;
	if (step.value === "key" && chosen.value?.connected)
		return __("Leave it empty to keep the key and check for new models.");
	return "";
});

// each field takes the focus as its step opens, so the whole flow runs from the keyboard
watch(step, async (now) => {
	if (now !== "url" && now !== "key") return;
	await nextTick();
	root.value?.querySelector("input")?.focus();
});

// the select opens with its search focused, so typing searches at once
const pick = async () => {
	step.value = "pick";
	isPickerOpen.value = true;
	await nextTick();
	picker.value?.focus();
	if (!presets.value.length) await loadPresets();
};

// read before the select acts on the key, so the Enter that picks a provider does not also continue
const continueOnEnter = (event: KeyboardEvent) => {
	if (isPickerOpen.value || !chosen.value) return;
	event.preventDefault();
	event.stopPropagation();
	next();
};

/** from the chosen provider to what it asks for: a sign-in, a base URL, then a key */
const next = () => {
	error.value = "";
	if (chosen.value?.oauth) return startSignIn();
	if (!chosen.value?.custom || step.value === "key") return (step.value = "key");
	if (step.value !== "url") return (step.value = "url");
	if (/^https?:\/\/\S+$/.test(url.value)) step.value = "key";
	else error.value = __("Enter a URL that starts with http:// or https://");
};

const cancel = () => {
	stopSignIn();
	if (props.preset) return emit("close");
	step.value = "start";
	chosen.value = null;
	signIn.value = null;
	url.value = "";
	apiKey.value = "";
	error.value = "";
};

const finish = async (result: ConnectResult | null) => {
	if (result) await connected(setup, result);
	emit("connected");
	cancel();
};

const connect = async () => {
	error.value = "";
	isConnecting.value = true;
	try {
		if (chosen.value?.custom) {
			await connectEndpoint(url.value.replace(/\/+$/, ""), apiKey.value);
			return await finish(null);
		}
		if (!apiKey.value && !chosen.value?.connected) throw new Error(__("Paste a key first"));
		const result = await api<ConnectResult>("builder.ai.api.connect_ai_provider", {
			preset: chosen.value?.id,
			api_key: apiKey.value,
		});
		await finish(result);
	} catch (e) {
		error.value = getErrorMessage(e, __("Could not connect"));
	} finally {
		isConnecting.value = false;
	}
};

const openKeyPage = () => window.open(chosen.value?.key_url, "_blank", "noopener");

/** ChatGPT signs in with a device code, so nothing has to redirect back to this site */
const startSignIn = async () => {
	step.value = "device";
	signInNote.value = "";
	const login = await api<DeviceSignIn>("builder.ai.api.start_codex_login").catch(() => null);
	if (!login?.code) return (error.value = login?.message || __("Could not start the sign-in"));
	signIn.value = login;
	stopSignIn = pollDeviceSignIn(login, {
		approved: () => (signInNote.value = __("Approved. Connecting to ChatGPT…")),
		connected: finish,
		failed: (message) => (error.value = message || __("The code expired. Cancel and start again.")),
	});
};

const copyAndOpen = () => {
	if (!signIn.value) return;
	navigator.clipboard?.writeText(signIn.value.code).catch(() => null);
	window.open(signIn.value.url, "_blank", "noopener");
	signInNote.value = __("Code copied. Waiting for you to approve it on ChatGPT…");
};
</script>
