<template>
	<div class="flex h-full min-h-0 flex-col">
		<div class="flex shrink-0 items-center gap-1 bg-surface-base px-2 py-3">
			<Button variant="ghost" size="sm" icon-left="lucide-arrow-left" label="Back" @click="emit('back')" />
		</div>

		<div class="no-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto">
			<p v-if="error" class="px-3 pb-3 text-p-sm text-ink-red-6">{{ error }}</p>
			<div v-else-if="!details" class="flex flex-1 items-center justify-center">
				<LoadingIndicator class="size-5 text-ink-gray-5" />
			</div>

			<div v-else class="flex flex-col gap-5 px-3 pb-5">
				<div class="flex items-start gap-3">
					<img
						v-if="details.icon"
						:src="details.icon"
						class="size-8 shrink-0 object-contain"
						alt=""
						aria-hidden="true" />
					<span v-else class="lucide-plug size-8 shrink-0 text-ink-gray-6" aria-hidden="true" />
					<div class="flex min-w-0 flex-col gap-0.5">
						<span class="truncate text-base text-ink-gray-9">{{ details.label }}</span>
						<span class="truncate text-xs text-ink-gray-5">{{ details.name }}</span>
						<div class="flex items-center gap-1.5">
							<span class="text-xs text-ink-gray-5">Version {{ details.version }}</span>
							<Badge v-if="details.is_development" size="sm" theme="orange" label="Dev" />
						</div>
					</div>
				</div>

				<p v-if="details.description" class="text-p-sm text-ink-gray-7">{{ details.description }}</p>

				<Button
					v-if="!isInstalled"
					variant="solid"
					size="sm"
					icon-left="lucide-download"
					label="Install"
					:loading="working"
					@click="askInstall" />

				<div v-else-if="details.is_development" class="flex gap-2">
					<Button
						v-if="mounted && canOpen(mounted)"
						variant="solid"
						size="sm"
						icon-left="lucide-panel-right"
						label="Open"
						@click="open" />
					<Button variant="subtle" size="sm" icon-left="lucide-unplug" label="Stop" @click="stop" />
				</div>

				<div v-else-if="isPending" class="flex flex-col gap-2">
					<div class="flex items-center gap-2 text-p-sm text-ink-gray-6">
						<LoadingIndicator class="size-4" />
						Installing this extension…
					</div>
					<Button variant="ghost" size="sm" label="Cancel" :loading="working" @click="discardInstall" />
				</div>

				<div v-else-if="isFailed" class="flex flex-col gap-2">
					<p class="text-p-sm text-ink-red-6">{{ details.install_error || "The install did not finish." }}</p>
					<div class="flex gap-2">
						<Button
							variant="solid"
							size="sm"
							icon-left="lucide-refresh-cw"
							label="Retry"
							:loading="working"
							@click="askInstall" />
						<Button
							variant="subtle"
							theme="red"
							size="sm"
							icon-left="lucide-trash-2"
							label="Remove"
							:loading="working"
							@click="discardInstall" />
					</div>
				</div>

				<ExtensionActions
					v-else
					:can-open="Boolean(mounted && canOpen(mounted))"
					:enabled="details.enabled"
					:working="working"
					@open="open"
					@set-enabled="setEnabled"
					@uninstall="uninstall" />

				<!-- eslint-disable-next-line vue/no-v-html -- renderMarkdown sanitizes through DOMPurify -->
				<div
					v-if="readme"
					class="extension-readme markdown-body prose prose-sm max-w-none break-words border-t border-outline-gray-1 pt-4 text-p-sm text-ink-gray-7"
					v-html="readme" />

				<section v-if="isInstalled && isReady" class="border-t border-outline-gray-1 py-4">
					<div class="pb-3">
						<h2 class="text-sm font-medium text-ink-gray-8">Capabilities</h2>
						<p class="pt-2 text-xs text-ink-gray-5">
							Control what {{ details.label }} may do in Builder and on this site.
							<template v-if="details.is_development">
								Loading it again restores what its manifest asks for.
							</template>
						</p>
					</div>
					<ExtensionCapabilities
						:extension="details.name"
						:label="details.label ?? details.name"
						:requested="details.requested_capabilities"
						:granted="details.granted_capabilities"
						:doctype-grants="details.doctype_grants"
						@update:granted="grant"
						@doctype-grants="refreshDetails" />
				</section>

				<div class="flex flex-col gap-1 border-t border-outline-gray-1 pt-4 text-xs text-ink-gray-5">
					<p v-if="!isInstalled">{{ details.source_url || "From the Builder Hub" }}</p>
					<p v-else-if="details.is_development">Served by {{ details.development_server }}</p>
					<template v-else-if="isReady">
						<p>{{ details.source_url || "Installed from a directory" }}</p>
						<p>Installed on {{ installedOn }}</p>
					</template>
				</div>
			</div>
		</div>

		<ExtensionInstallDialog
			v-if="details"
			v-model:open="isInstallDialogOpen"
			:extension="details.name"
			:label="details.label ?? details.name"
			:requested="releaseCapabilities"
			@install="install" />
	</div>
</template>

<script setup lang="ts">
import ExtensionActions from "@/components/LeftPanelTabs/Extensions/ExtensionActions.vue";
import ExtensionCapabilities from "@/components/LeftPanelTabs/Extensions/ExtensionCapabilities.vue";
import ExtensionInstallDialog from "@/components/LeftPanelTabs/Extensions/ExtensionInstallDialog.vue";
import { renderMarkdown } from "@/components/ai/markdown";
import {
	installedExtensions,
	useInstallationDetails,
	getHubExtension,
	getHubReleaseCapabilities,
	installFromHub,
	setExtensionEnabled,
	setGrantedCapabilities,
	uninstallExtension,
	uninstallSummary,
	type InstallationDetails,
} from "@/data/extensions";
import { stopDevExtension } from "@/extensions/devExtension";
import { canOpen, openExtension } from "@/extensions/surfaces/openMethods";
import useBuilderStore from "@/stores/builderStore";
import { confirm } from "@/utils/helpers";
import type { Capability } from "frappe-builder-extension-sdk/types";
import { Badge, Button, LoadingIndicator, toast } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from "vue";

const props = defineProps<{ extension: string; isInstalled: boolean }>();
const emit = defineEmits<{ back: [] }>();

const builderStore = useBuilderStore();

const activeInstallation = shallowRef<ReturnType<typeof useInstallationDetails> | null>(null);
const hubDetails = ref<InstallationDetails | null>(null);
const details = computed(() => activeInstallation.value?.details.value ?? hubDetails.value);
const error = ref("");
const working = ref(false);

/** A Hub install is "Installing" until its job lands, then "Ready" or "Failed". An
 * install from any other path, and an older row, has no state and reads as ready. */
const isPending = computed(() => details.value?.install_state === "Installing");
const isFailed = computed(() => details.value?.install_state === "Failed");
const isReady = computed(() => !isPending.value && !isFailed.value);

/** The running record, which a disabled extension does not have. Its open target needs a frame. */
const mounted = computed(() => installedExtensions.value.find((row) => row.name === props.extension));

const open = () => mounted.value && openExtension(mounted.value);

const stop = () => {
	stopDevExtension();
	emit("back");
};

const readme = computed(() => (details.value?.readme ? renderMarkdown(details.value.readme) : ""));

const installedOn = computed(() =>
	details.value ? new Date(details.value.installed_on).toLocaleDateString() : "",
);

const load = async () => {
	activeInstallation.value = null;
	hubDetails.value = null;
	error.value = "";
	try {
		if (props.isInstalled) {
			const installation = useInstallationDetails(props.extension);
			activeInstallation.value = installation;
			await installation.reload();
		} else {
			hubDetails.value = fromHub(await getHubExtension(props.extension));
		}
	} catch (thrown) {
		error.value = (thrown as Error).message;
	}
};

/** A hub entry seen through the same shape, minus what only an installation holds. */
const fromHub = (hub: Awaited<ReturnType<typeof getHubExtension>>): InstallationDetails => ({
	...hub,
	source_url: hub.source_url ?? "",
	enabled: false,
	installed_on: "",
	requested_capabilities: [],
	granted_capabilities: [],
	doctype_grants: [],
});

const isInstallDialogOpen = ref(false);
const releaseCapabilities = ref<Capability[]>([]);

/** Serves the Marketplace "Install" and the "Retry" on a failed row. The dialog
 * lists what the exact release asks for, so the install pins that version. */
const askInstall = async () => {
	working.value = true;
	try {
		releaseCapabilities.value = await getHubReleaseCapabilities(props.extension, details.value!.version);
		isInstallDialogOpen.value = true;
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

/** Retry stays on the page to show progress; a fresh install goes back to the list. */
const install = async (capabilities: Capability[]) => {
	isInstallDialogOpen.value = false;
	working.value = true;
	try {
		await installFromHub(props.extension, details.value!.version, capabilities);
		toast.success("Installing…");
		if (props.isInstalled) await load();
		else emit("back");
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

/** Cancel a stuck install or clear a failed one. Neither made anything, so this
 * needs no uninstall summary or confirmation. */
const discardInstall = async () => {
	working.value = true;
	try {
		await uninstallExtension(props.extension);
		toast.success("Removed");
		emit("back");
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

watch([() => props.extension, () => props.isInstalled], load, { immediate: true });

/**
 * The underlying resources are realtime, so this is only an immediate refresh
 * rather than a wait for the round trip — not the only thing that keeps
 * `details` current.
 */
const refreshDetails = () => activeInstallation.value?.reload();

const grant = async (capabilities: Capability[]) => {
	try {
		await setGrantedCapabilities(props.extension, capabilities);
		await refreshDetails();
	} catch (thrown) {
		toast.error((thrown as Error).message);
	}
};

/** The install job finishes elsewhere. Reload this page when it touches this extension. */
const onInstallDone = (event: { extension: string }) => {
	if (event.extension === props.extension) load();
};

onMounted(() => builderStore.realtime.on("builder_extension_install", onInstallDone));
onUnmounted(() => builderStore.realtime.off("builder_extension_install", onInstallDone));

/** Disabling unmounts every frame, so the panel has to say what it did. */
const setEnabled = async (enabled: boolean) => {
	working.value = true;
	try {
		await setExtensionEnabled(props.extension, enabled);
		await load();
		toast.success(enabled ? "Extension enabled" : "Extension disabled");
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

/**
 * The summary is read before the question, because what the site keeps is the
 * part a user cannot guess: a token styles pages they already published.
 */
const uninstall = async () => {
	working.value = true;
	try {
		const summary = await uninstallSummary(props.extension);
		if (await confirm(uninstallMessage(summary), `Uninstall ${details.value?.label}?`)) {
			await uninstallExtension(props.extension);
			toast.success("Extension uninstalled");
			emit("back");
		}
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

const uninstallMessage = (summary: Awaited<ReturnType<typeof uninstallSummary>>) => {
	const kept = summary.resources.map((made) => `${made.count} ${made.resource_type}`);
	if (summary.tokens) kept.push(`${summary.tokens} design token(s)`);

	const lines = ["This removes your copy, your grants and what the extension remembered."];
	if (kept.length) lines.push(`The site keeps ${kept.join(", ")}, because published pages use them.`);
	if (summary.other_users) lines.push(`${summary.other_users} other user(s) still have it installed.`);
	return lines.join(" ");
};
</script>

<style scoped>
/* The panel is 300 pixels wide, so anything that cannot wrap has to scroll in
 * its own box rather than push the column. */
.extension-readme :deep(pre),
.extension-readme :deep(table) {
	overflow-x: auto;
	display: block;
	max-width: 100%;
}
</style>
