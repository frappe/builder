<template>
	<div class="flex h-full min-h-0 flex-col gap-5">
		<!-- Steps you've already cleared stay clickable, so this doubles as the way
		     back; the ones ahead are disabled because they need this one answered. -->
		<TabButtons
			class="shrink-0"
			type="underline"
			:modelValue="step"
			:options="stepOptions"
			@update:modelValue="goToStep" />

		<!-- 1 · pick a provider -->
		<div v-if="step === 0" class="flex min-h-0 flex-1 flex-col gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="text-p-base font-medium text-ink-gray-9">Connect a model</h3>
				<p class="text-p-sm text-ink-gray-6">
					Builder needs somewhere to send its requests. Pick who you already have an account with.
				</p>
			</div>
			<div v-if="loadError" class="rounded-lg bg-surface-red-1 p-3 text-p-sm text-ink-red-6">
				{{ loadError }}
			</div>
			<p v-else-if="loading" class="text-p-sm text-ink-gray-5">Loading providers…</p>
			<!-- content-start + auto-rows-min: a grid defaults to align-content stretch,
			     so the rows grew to fill the panel and each card became a tall slab. -->
			<div
				v-else
				class="grid min-h-0 flex-1 auto-rows-min grid-cols-2 content-start gap-2.5 overflow-y-auto pb-2">
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
			<div class="flex flex-col gap-1">
				<h3 class="text-p-base font-medium text-ink-gray-9">
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

			<FormControl
				v-if="active.needs_name"
				v-model="providerName"
				label="Provider name"
				placeholder="Frappe AI"
				autocomplete="off" />

			<div v-if="active.needs_api_base" class="flex flex-col gap-1.5">
				<FormControl v-model="apiBase" label="Base URL" placeholder="http://localhost:11434/v1" />
				<p class="text-p-xs text-ink-gray-5">Anything that speaks the OpenAI API.</p>
			</div>

			<!-- An OAuth provider signs in with a browser round-trip; there is no key
			     to paste. The tokens stay server-side, the UI only polls for the outcome. -->
			<div v-if="active.oauth" class="flex flex-col gap-3">
				<div class="flex items-center gap-2">
					<Button size="sm" variant="solid" :loading="oauthStatus === 'waiting'" @click="signIn">
						{{ oauthStatus === "waiting" ? "Waiting for sign-in" : "Sign in with ChatGPT" }}
					</Button>
					<Badge v-if="oauthStatus === 'connected'" theme="green" size="sm" label="Connected" />
					<Badge
						v-else-if="active.has_key && oauthStatus === 'idle'"
						theme="green"
						size="sm"
						label="Already connected" />
				</div>
				<p v-if="active.has_key && oauthStatus === 'idle'" class="text-p-xs text-ink-gray-5">
					Sign in again to switch accounts, or continue with the stored one.
				</p>
				<!-- The redirect goes to localhost:1455. When this server can't be there to
				     catch it, the browser strands on a dead page whose address still carries
				     the sign-in code, so pasting that address completes the same login. -->
				<div v-if="oauthStatus === 'waiting'" class="flex flex-col gap-1.5">
					<FormControl
						v-model="pasteUrl"
						label="Didn't connect on its own?"
						placeholder="http://localhost:1455/auth/callback?code=…"
						autocomplete="off" />
					<p class="text-p-xs text-ink-gray-5">
						If the sign-in tab ends on a localhost page that can't load, paste that page's address here.
					</p>
					<Button
						v-if="pasteUrl.trim()"
						size="sm"
						variant="subtle"
						class="w-fit"
						:loading="busy"
						@click="connectPasted">
						Connect
					</Button>
				</div>
				<p v-if="result" class="text-p-xs" :class="resultClass">{{ result.message }}</p>
			</div>

			<div v-else class="flex flex-col gap-1.5">
				<FormControl
					v-model="apiKey"
					type="password"
					:label="`API key${active.custom ? ' (if it needs one)' : ''}`"
					:placeholder="keyPlaceholder"
					autocomplete="off" />
				<p v-if="result" class="text-p-xs" :class="resultClass">
					{{ result.message }}
					<template v-if="result.severity === 'warn'">
						You can finish setting up and sort that out later.
					</template>
				</p>
				<!-- Only the connected case needs a note: the placeholder already tells a
				     first-time user what shape of key goes here. -->
				<p v-else-if="active.has_key" class="text-p-xs text-ink-gray-5">
					Leave blank to keep the stored key.
				</p>
			</div>

			<div v-if="active.custom" class="flex flex-col gap-1.5">
				<FormControl
					v-model="customModels"
					type="textarea"
					label="Models"
					:rows="3"
					placeholder="laguna-s-2.1&#10;deepseek-v4-flash" />
				<p class="text-p-xs text-ink-gray-5">One model id per line, exactly as the endpoint names them.</p>
			</div>
		</div>

		<!-- 3 · models -->
		<div v-else class="flex min-h-0 flex-1 flex-col gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="text-p-base font-medium text-ink-gray-9">Choose models</h3>
				<p class="text-p-sm text-ink-gray-6">
					These appear in the chat's model picker. You can change them any time.
				</p>
			</div>
			<div class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pb-2">
				<!-- Checkbox draws its own label and description; the card around it
				     carries the selected state and is clickable too, since a row that
				     looks pressable but only responds on the box itself reads as broken.
				     click.stop on the Checkbox keeps its own toggle from also bubbling to
				     the card and cancelling itself out. -->
				<div
					v-for="m in active.models"
					:key="m.model_id"
					class="ai-model-row cursor-pointer rounded-lg border p-3 transition-colors"
					:class="
						selected.includes(m.model_id)
							? 'border-outline-gray-4 bg-surface-gray-2'
							: 'border-outline-gray-2 hover:border-outline-gray-3'
					"
					@click="toggle(m.model_id)">
					<!-- The ROW is the control and `selected` is the only state; the
					     checkbox just displays it. Letting the input take clicks too meant
					     two owners: a click on the label flipped the DOM checkbox without
					     the emit reaching us, so the box looked ticked while the model was
					     never actually selected, and Finish saved fewer than were showing. -->
					<Checkbox
						class="pointer-events-none"
						:modelValue="selected.includes(m.model_id)"
						:description="m.note">
						<template #label>
							<span class="flex items-center gap-1.5">
								<span class="text-p-sm font-medium text-ink-gray-8">{{ m.label }}</span>
								<Badge v-if="m.recommended" theme="blue" size="sm" label="Recommended" />
							</span>
						</template>
					</Checkbox>
				</div>
			</div>
		</div>

		<div class="flex items-center justify-between border-t border-outline-gray-1 pt-3">
			<!-- On step 0 there's no earlier step, but there IS somewhere to go back to
			     when the flow was opened from the model list to add another provider. -->
			<Button v-if="step > 0 || canSkipSetup" size="sm" variant="ghost" @click="back">Back</Button>
			<span v-else />
			<div class="flex items-center gap-2">
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
import { reloadAIRegistry } from "@/data/aiModels";
import { Badge, Button, Checkbox, createResource, FormControl, TabButtons, toast } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref } from "vue";

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
	oauth: boolean;
	has_key: boolean;
	needs_name: boolean;
	needs_api_base: boolean;
	configured: boolean;
	models: { model_id: string; label: string; note: string; recommended: boolean }[];
};

const stepLabels = ["Provider", "Connect", "Models"];
const step = ref(0);
// How far the flow has been taken, so stepping back doesn't lock the later steps
// away again.
const reached = ref(0);
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

// The browser sign-in for OAuth providers: idle until the button starts one,
// waiting while the tab is out, then connected or failed. `loginState` pairs
// the polls with the attempt they belong to.
const oauthStatus = ref<"idle" | "waiting" | "connected" | "failed">("idle");
const pasteUrl = ref("");
let loginState = "";
let pollTimer: number | undefined;

const resultClass = computed(() =>
	result.value?.success
		? "text-ink-green-6"
		: result.value?.severity === "warn"
			? "text-ink-amber-6"
			: "text-ink-red-6",
);

// Numbered because the steps are gated, not browsable: the count tells you how
// far this goes and which one you're on. The label is fixed, so unlike the tick
// it used to swap in, nothing about it moves between steps.
const stepOptions = computed(() =>
	stepLabels.map((label, i) => ({ label: `${i + 1}. ${label}`, value: i, disabled: i > reached.value })),
);

const keyPlaceholder = computed(() => {
	if (active.value.has_key) return "Stored, leave blank to keep it";
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
	if (active.value.oauth) return oauthStatus.value === "connected" || active.value.has_key;
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
	stopPolling();
	oauthStatus.value = "idle";
	pasteUrl.value = "";
	// Recommended models come pre-ticked so a known provider is two clicks and a
	// paste: the point of the presets is that nothing else needs deciding.
	selected.value = preset.models.filter((m) => m.recommended).map((m) => m.model_id);
	// A different provider invalidates everything chosen after it.
	reached.value = 1;
	goTo(1);
};

const goTo = (n: number) => {
	step.value = n;
	reached.value = Math.max(reached.value, n);
};

const goToStep = (value: unknown) => {
	const n = Number(value);
	if (n <= reached.value) {
		result.value = null;
		step.value = n;
	}
};

const back = () => {
	result.value = null;
	// Back off step 0 leaves the flow entirely, returning to the model list.
	if (step.value === 0) {
		emit("done");
		return;
	}
	step.value -= 1;
};

const proceed = () => {
	if (active.value.custom) selected.value = customModelIds.value;
	goTo(2);
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

const signIn = async () => {
	result.value = null;
	try {
		const res: any = await createResource({ url: "builder.ai.api.start_codex_login" }).submit();
		loginState = res.state;
		window.open(res.url, "_blank", "noopener");
		oauthStatus.value = "waiting";
		pollTimer = window.setInterval(pollLogin, 2500);
	} catch (error) {
		loginFailed((error as Error).message || "Could not start the sign-in");
	}
};

const pollLogin = async () => {
	try {
		const res: any = await createResource({ url: "builder.ai.api.poll_codex_login" }).submit({
			state: loginState,
		});
		if (res.status === "connected") loginDone();
		else if (res.status === "failed") loginFailed(res.message);
		else if (res.status === "expired") loginFailed("The sign-in expired. Try again.");
	} catch {
		// a dropped poll is not a failed login; the next tick retries
	}
};

const connectPasted = async () => {
	busy.value = true;
	try {
		const res: any = await createResource({ url: "builder.ai.api.finish_codex_login" }).submit({
			redirect_url: pasteUrl.value.trim(),
		});
		if (res.status === "connected") loginDone();
		else loginFailed(res.message || "Could not complete the sign-in");
	} catch (error) {
		loginFailed((error as Error).message || "Could not complete the sign-in");
	} finally {
		busy.value = false;
	}
};

const loginDone = () => {
	stopPolling();
	oauthStatus.value = "connected";
	// The provider row now holds the credential, which is exactly what has_key
	// reports after a reload; keep the local copy truthful too.
	active.value.has_key = true;
	result.value = { success: true, severity: "ok", message: "Signed in with ChatGPT" };
};

const loginFailed = (message: string) => {
	stopPolling();
	oauthStatus.value = "failed";
	result.value = { success: false, severity: "error", message: message || "Sign-in failed" };
};

const stopPolling = () => {
	if (pollTimer) window.clearInterval(pollTimer);
	pollTimer = undefined;
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
			toast.success(`${installed} model${installed === 1 ? "" : "s"} connected`);
		}
		emit("done");
	} catch (error) {
		toast.error((error as Error).message || "Could not save the provider");
	} finally {
		busy.value = false;
	}
};

onMounted(load);
onUnmounted(stopPolling);
</script>

<style>
/* frappe-ui's Checkbox draws its tick as an SVG with fill #0F0F0F, sized for a
   light box. In dark mode the box stays dark too, so it's a near-black tick on a
   near-black square and a ticked model looks unticked. Lifting the checked
   background to ink-gray-9 (near-white in dark) gives that tick something to sit
   on. Light mode already works, so it is left alone. */
[data-theme="dark"] .ai-model-row input[type="checkbox"]:checked {
	background-color: var(--ink-gray-9);
	border-color: var(--ink-gray-9);
}
</style>
