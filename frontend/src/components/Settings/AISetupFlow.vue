<template>
	<div class="flex h-full min-h-0 flex-col gap-5">
		<div class="flex items-center gap-2">
			<template v-for="(s, i) in stepLabels" :key="s">
				<span
					class="text-p-xs"
					:class="
						i === step ? 'font-medium text-ink-gray-8' : i < step ? 'text-ink-gray-6' : 'text-ink-gray-4'
					">
					{{ i < step ? "✓" : i + 1 }}. {{ s }}
				</span>
				<span v-if="i < stepLabels.length - 1" class="bg-outline-gray-2 h-px w-4" />
			</template>
		</div>

		<!-- 1 · pick a provider -->
		<div v-if="step === 0" class="flex min-h-0 flex-1 flex-col gap-3">
			<div class="flex flex-col">
				<h3 class="text-base font-medium text-ink-gray-9">Connect a model</h3>
				<p class="text-p-sm text-ink-gray-6">
					Builder needs somewhere to send its requests. Pick who you already have an account with.
				</p>
			</div>
			<div v-if="loadError" class="rounded-lg bg-surface-red-1 p-3 text-p-sm text-ink-red-6">
				{{ loadError }}
			</div>
			<p v-else-if="loading" class="text-p-sm text-ink-gray-5">Loading providers…</p>
			<div v-else class="grid min-h-0 flex-1 grid-cols-2 gap-2.5 overflow-y-auto pb-2">
				<button
					v-for="preset in presets"
					:key="preset.id"
					class="group flex flex-col gap-1 rounded-lg border p-3.5 text-left transition-colors"
					:class="
						preset.configured
							? 'border-outline-gray-2 bg-surface-gray-1 hover:border-outline-gray-3'
							: 'border-outline-gray-2 hover:border-outline-gray-4 hover:bg-surface-gray-1'
					"
					@click="choose(preset)">
					<span class="flex items-center gap-1.5">
						<span class="text-p-sm font-medium text-ink-gray-8">
							{{ preset.name || "Custom" }}
						</span>
						<Badge v-if="preset.configured" theme="green" size="sm" label="Connected" />
					</span>
					<span class="text-p-xs text-ink-gray-5">{{ preset.tagline }}</span>
				</button>
			</div>
		</div>

		<!-- 2 · credentials -->
		<div v-else-if="step === 1" class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
			<div class="flex flex-col">
				<h3 class="text-base font-medium text-ink-gray-9">
					{{ active.custom ? "Describe your endpoint" : `Connect ${active.name}` }}
				</h3>
				<p class="text-p-sm text-ink-gray-6">{{ active.blurb }}</p>
			</div>

			<ol v-if="active.key_steps?.length" class="flex flex-col gap-1.5 pl-1">
				<li v-for="(s, i) in active.key_steps" :key="s" class="flex gap-2 text-p-sm text-ink-gray-7">
					<span class="text-ink-gray-4">{{ i + 1 }}</span>
					<span>{{ s }}</span>
				</li>
			</ol>
			<a v-if="active.key_url" :href="active.key_url" target="_blank" rel="noopener" class="w-fit">
				<Button size="sm" variant="subtle" iconRight="lucide-external-link">Open key page</Button>
			</a>

			<div v-if="active.needs_name" class="flex flex-col gap-1.5">
				<InputLabel>Provider name</InputLabel>
				<BuilderInput
					type="text"
					:autofocus="true"
					:modelValue="providerName"
					@update:modelValue="(v: string) => (providerName = v)"
					placeholder="Frappe AI"
					:hideClearButton="true" />
			</div>

			<div v-if="active.needs_api_base" class="flex flex-col gap-1.5">
				<InputLabel>Base URL</InputLabel>
				<BuilderInput
					type="text"
					:modelValue="apiBase"
					@update:modelValue="(v: string) => (apiBase = v)"
					placeholder="http://localhost:11434/v1"
					:hideClearButton="true" />
				<p class="text-p-xs text-ink-gray-5">Anything that speaks the OpenAI API.</p>
			</div>

			<div class="flex flex-col gap-1.5">
				<InputLabel>API key{{ active.custom ? " (if it needs one)" : "" }}</InputLabel>
				<BuilderInput
					type="password"
					:autofocus="!active.needs_name"
					:modelValue="apiKey"
					@update:modelValue="(v: string) => (apiKey = v)"
					:placeholder="keyPlaceholder"
					:hideClearButton="true" />
				<p v-if="result" class="text-p-xs" :class="resultClass">
					{{ result.message }}
					<template v-if="result.severity === 'warn'">
						You can finish setting up and sort that out later.
					</template>
				</p>
				<p v-else-if="active.has_key" class="text-p-xs text-ink-gray-5">
					Already connected. Leave this blank to keep the stored key, or paste a new one to replace it.
				</p>
				<p v-else-if="!active.custom" class="text-p-xs text-ink-gray-5">
					Stored on this site and never shown again.
				</p>
			</div>

			<div v-if="active.custom" class="flex flex-col gap-1.5">
				<InputLabel>Models</InputLabel>
				<BuilderInput
					type="textarea"
					:modelValue="customModels"
					@update:modelValue="(v: string) => (customModels = v)"
					placeholder="laguna-s-2.1&#10;deepseek-v4-flash"
					:hideClearButton="true" />
				<p class="text-p-xs text-ink-gray-5">One model id per line, exactly as the endpoint names them.</p>
			</div>
		</div>

		<!-- 3 · models -->
		<div v-else class="flex min-h-0 flex-1 flex-col gap-3">
			<div class="flex flex-col">
				<h3 class="text-base font-medium text-ink-gray-9">Choose models</h3>
				<p class="text-p-sm text-ink-gray-6">
					These appear in the chat's model picker. You can change them any time.
				</p>
			</div>
			<div class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pb-2">
				<!-- A div, not a label: a label wrapping a checkbox forwards the click to
				     the input as well as firing its own, so one tap can toggle twice and
				     land back where it started. -->
				<div
					v-for="m in active.models"
					:key="m.model_id"
					class="flex cursor-pointer items-start gap-3 rounded-lg border border-outline-gray-2 p-3"
					@click="toggle(m.model_id)">
					<Checkbox
						class="pointer-events-none mt-0.5"
						:modelValue="selected.includes(m.model_id)"
						@update:modelValue="() => {}" />
					<span class="flex min-w-0 flex-col">
						<span class="flex items-center gap-1.5">
							<span class="text-p-sm font-medium text-ink-gray-8">{{ m.label }}</span>
							<Badge v-if="m.recommended" theme="blue" size="sm" label="Recommended" />
						</span>
						<span class="text-p-xs text-ink-gray-5">{{ m.note }}</span>
					</span>
				</div>
			</div>
		</div>

		<div class="flex items-center justify-between border-t border-outline-gray-1 pt-3">
			<Button v-if="step > 0" size="sm" variant="ghost" @click="back">Back</Button>
			<span v-else />
			<div class="flex items-center gap-2">
				<Button v-if="canSkipSetup" size="sm" variant="ghost" @click="$emit('done')">
					I'll do this later
				</Button>
				<!-- Never a dead end: a rejected key can still be saved and fixed later,
				     it just shouldn't be the button your eye lands on. -->
				<Button
					v-if="step === 1 && result && result.severity === 'error'"
					size="sm"
					variant="ghost"
					@click="proceed">
					Continue anyway
				</Button>
				<Button
					v-if="step === 1"
					size="sm"
					variant="solid"
					:loading="busy"
					:disabled="!canContinue"
					@click="verify">
					{{ continueLabel }}
				</Button>
				<Button
					v-else-if="step === 2"
					size="sm"
					variant="solid"
					:loading="busy"
					:disabled="!selected.length"
					@click="finish">
					Finish
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { reloadAIRegistry } from "@/data/aiModels";
import { Badge, Button, Checkbox, createResource, toast } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

defineProps<{ canSkipSetup?: boolean }>();
const emit = defineEmits(["done"]);

type Preset = {
	id: string;
	name: string;
	tagline: string;
	blurb: string;
	key_url: string;
	key_prefix: string;
	key_steps: string[];
	api_base: string | null;
	custom: boolean;
	has_key: boolean;
	needs_name: boolean;
	needs_api_base: boolean;
	configured: boolean;
	models: { model_id: string; label: string; note: string; recommended: boolean }[];
};

const stepLabels = ["Provider", "Connect", "Models"];
const step = ref(0);
const presets = ref<Preset[]>([]);
const active = ref<Preset>({} as Preset);
const providerName = ref("");
const apiBase = ref("");
const apiKey = ref("");
const customModels = ref("");
const selected = ref<string[]>([]);
type Result = { success: boolean; severity: "ok" | "warn" | "error"; message: string };

const result = ref<Result | null>(null);
const busy = ref(false);
const loading = ref(true);
const loadError = ref("");

const resultClass = computed(() =>
	result.value?.success
		? "text-ink-green-6"
		: result.value?.severity === "warn"
			? "text-ink-amber-6"
			: "text-ink-red-6",
);

const keyPlaceholder = computed(() => {
	if (active.value.has_key) return "Stored — leave blank to keep it";
	return active.value.key_prefix ? `${active.value.key_prefix}…` : "Leave empty if not required";
});

const continueLabel = computed(() => {
	if (!result.value) return "Test connection";
	if (result.value.success) return "Continue";
	// The credentials checked out; the account just needs attention elsewhere.
	return result.value.severity === "warn" ? "Continue" : "Test again";
});

const customModelIds = computed(() =>
	customModels.value
		.split("\n")
		.map((m) => m.trim())
		.filter(Boolean),
);

const canContinue = computed(() => {
	if (active.value.needs_name && !providerName.value.trim()) return false;
	if (active.value.needs_api_base && !apiBase.value.trim()) return false;
	if (active.value.custom) return customModelIds.value.length > 0;
	// An already-connected provider has a key the site can use but can't show, so
	// an empty box means "keep it" rather than "nothing entered".
	return !!apiKey.value.trim() || active.value.has_key;
});

const load = async () => {
	loading.value = true;
	try {
		const state: any = await createResource({ url: "builder.ai.api.ai_setup_state" }).submit();
		presets.value = state.presets || [];
		if (state.needs_migrate) {
			loadError.value = "This site is missing Builder's AI tables. Run bench migrate on it, then reopen.";
		} else if (!presets.value.length) {
			loadError.value = "No providers came back from the server.";
		}
	} catch (error) {
		// Without this the screen renders its heading over an empty grid and says
		// nothing, which reads as "there are no providers" rather than "it broke".
		loadError.value = (error as Error).message || "Could not load the provider list.";
	} finally {
		loading.value = false;
	}
};

const choose = (preset: Preset) => {
	active.value = preset;
	providerName.value = preset.name;
	apiBase.value = preset.api_base || "";
	apiKey.value = "";
	customModels.value = "";
	result.value = null;
	// Recommended models come pre-ticked so a known provider is two clicks and a
	// paste: the point of the presets is that nothing else needs deciding.
	selected.value = preset.models.filter((m) => m.recommended).map((m) => m.model_id);
	step.value = 1;
};

const back = () => {
	result.value = null;
	step.value -= 1;
};

const proceed = () => {
	if (active.value.custom) selected.value = customModelIds.value;
	step.value = 2;
};

const verify = async () => {
	// Pressing again on a result that already cleared just moves on — a good key
	// shouldn't be re-billed, and a valid-but-broke account has nothing to retry.
	if (result.value && (result.value.success || result.value.severity === "warn")) {
		proceed();
		return;
	}
	busy.value = true;
	try {
		result.value = (await createResource({ url: "builder.ai.api.verify_ai_key" }).submit({
			preset: active.value.id,
			api_key: apiKey.value,
			api_base: apiBase.value,
			model_id: active.value.custom ? customModelIds.value[0] : "",
		})) as Result;
	} catch (error) {
		result.value = {
			success: false,
			severity: "error",
			message: (error as Error).message || "Could not reach the provider",
		};
	} finally {
		busy.value = false;
	}
};

const toggle = (id: string) => {
	const at = selected.value.indexOf(id);
	if (at === -1) selected.value.push(id);
	else selected.value.splice(at, 1);
};

const finish = async () => {
	busy.value = true;
	try {
		const res: any = await createResource({ url: "builder.ai.api.setup_ai_provider" }).submit({
			preset: active.value.id,
			api_key: apiKey.value,
			api_base: apiBase.value,
			// Sent as JSON, not a bare array: form encoding keeps only the first value,
			// which silently dropped every model after the one at the top of the list.
			models: JSON.stringify(selected.value),
			provider_name: providerName.value,
		});
		await reloadAIRegistry();
		// If the server switched on fewer than were ticked, the selection didn't
		// survive the trip. Say that rather than reporting success over it.
		const installed = (res.installed || []).length;
		if (installed < selected.value.length) {
			toast.error(`Only ${installed} of ${selected.value.length} models were saved. Reload and retry.`);
		} else {
			toast.success(`Ready — ${installed} model${installed === 1 ? "" : "s"} connected`);
		}
		emit("done");
	} catch (error) {
		toast.error((error as Error).message || "Could not save the provider");
	} finally {
		busy.value = false;
	}
};

onMounted(load);
</script>
