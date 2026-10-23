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
							<Badge v-if="details.is_development" size="sm" theme="amber" label="Dev" />
						</div>
					</div>
				</div>

				<p v-if="details.description" class="text-p-sm text-ink-gray-7">{{ details.description }}</p>

				<Tooltip
					v-if="!isInstalled"
					text="Only a System Manager or a Website Manager can install extensions."
					:disabled="canManageExtensions">
					<!-- a disabled button gets no hover events, so the tooltip listens on this box -->
					<div>
						<Button
							class="w-full"
							variant="solid"
							size="sm"
							icon-left="lucide-download"
							label="Install"
							:disabled="!canManageExtensions"
							:loading="isAskingInstall"
							@click="isInstallDialogOpen = true" />
					</div>
				</Tooltip>

				<div v-else-if="details.is_development" class="flex gap-2">
					<Button
						v-if="openHandler"
						variant="solid"
						size="sm"
						icon-left="lucide-panel-right"
						label="Open"
						@click="openHandler" />
					<Button variant="subtle" size="sm" icon-left="lucide-unplug" label="Stop" @click="stop" />
				</div>

				<div v-else-if="isPending" class="flex flex-col gap-2">
					<div class="flex items-center gap-2 text-p-sm text-ink-gray-6">
						<LoadingIndicator class="size-4" />
						Installing this extension…
					</div>
					<Button
						v-if="canManageExtensions"
						variant="ghost"
						size="sm"
						label="Cancel"
						:loading="working"
						@click="discardInstall" />
				</div>

				<div v-else-if="isFailed" class="flex flex-col gap-2">
					<p class="text-p-sm text-ink-red-6">{{ details.install_error || "The install did not finish." }}</p>
					<div v-if="canManageExtensions" class="flex gap-2">
						<Button
							variant="solid"
							size="sm"
							icon-left="lucide-refresh-cw"
							label="Retry"
							:loading="isAskingInstall"
							@click="isInstallDialogOpen = true" />
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
					:can-open="Boolean(openHandler)"
					:can-manage="canManageExtensions"
					:enabled="details.enabled"
					:working="working"
					@open="openHandler?.()"
					@set-enabled="setEnabled"
					@uninstall="uninstall" />

				<ExtensionUpdate
					v-if="
						canManageExtensions &&
						isInstalled &&
						isReady &&
						details.source === 'Hub' &&
						!details.is_development
					"
					:extension="details.name"
					@updated="load" />

				<!-- eslint-disable-next-line vue/no-v-html -- renderMarkdown sanitizes through DOMPurify -->
				<div
					v-if="readme"
					class="extension-readme markdown-body prose prose-sm max-w-none break-words border-t border-outline-gray-1 pt-4 text-p-sm text-ink-gray-7"
					v-html="readme" />

				<div class="flex flex-col gap-1 border-t border-outline-gray-1 pt-4 text-xs text-ink-gray-5">
					<p v-if="!isInstalled">{{ details.repository_url || "From the Builder Hub" }}</p>
					<p v-else-if="details.is_development">Served by {{ details.development_server }}</p>
					<template v-else-if="isReady">
						<p v-if="details.source === 'Hub'">{{ details.hub_url }}</p>
						<p>Installed on {{ installedOn }}</p>
					</template>
				</div>
			</div>
		</div>

		<ExtensionInstallDialog
			v-if="details"
			v-model:open="isInstallDialogOpen"
			:label="details.label ?? details.name"
			@install="install" />
	</div>
</template>

<script setup lang="ts">
import ExtensionActions from "@/components/LeftPanelTabs/Extensions/ExtensionActions.vue";
import ExtensionInstallDialog from "@/components/LeftPanelTabs/Extensions/ExtensionInstallDialog.vue";
import ExtensionUpdate from "@/components/LeftPanelTabs/Extensions/ExtensionUpdate.vue";
import { renderMarkdown } from "@/components/ai/markdown";
import {
	canManageExtensions,
	getHubExtension,
	installations,
	installFromHub,
	promptReload,
	reloadInstallations,
	setExtensionEnabled,
	uninstallExtension,
	useInstallationDetails,
	type InstallationDetails,
} from "@/data/extensions";
import { openHandlers } from "@/extensions/context";
import { stopDevExtension } from "@/extensions/devExtension";
import { confirm } from "@/utils/helpers";
import { Badge, Button, LoadingIndicator, toast, Tooltip } from "frappe-ui";
import { computed, ref, shallowRef, watch } from "vue";

const props = defineProps<{ extension: string }>();
const emit = defineEmits<{ back: [] }>();

const activeInstallation = shallowRef<ReturnType<typeof useInstallationDetails> | null>(null);
const hubDetails = ref<InstallationDetails | null>(null);
const details = computed(() => activeInstallation.value?.details.value ?? hubDetails.value);
const error = ref("");
const working = ref(false);

/** Reads the shared list. So a Hub install from this page changes it to the installation. */
const isInstalled = computed(() => installations.value.some((row) => row.name === props.extension));

/** A Hub install is "Installing" until its job ends. Then it is "Ready" or "Failed". */
const isPending = computed(() => details.value?.install_state === "Installing");
const isFailed = computed(() => details.value?.install_state === "Failed");
const isReady = computed(() => !isPending.value && !isFailed.value);

/** What the running extension registered for its Open button. A disabled extension registers nothing. */
const openHandler = computed(() => openHandlers.get(props.extension));

const stop = async () => {
	await stopDevExtension();
	await reloadInstallations();
	promptReload("Dev extension stopped");
	emit("back");
};

const readme = computed(() => (details.value?.readme ? renderMarkdown(details.value.readme) : ""));

const installedOn = computed(() =>
	details.value ? new Date(details.value.installed_on).toLocaleDateString() : "",
);

const load = async () => {
	activeInstallation.value = null;
	hubDetails.value = null;
	isInstallDialogOpen.value = false;
	error.value = "";
	try {
		if (isInstalled.value) {
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

/** A Hub entry in the same shape, without the fields that only an installation has. */
const fromHub = (hub: Awaited<ReturnType<typeof getHubExtension>>): InstallationDetails => ({
	...hub,
	installation_id: "",
	source: "Hub",
	enabled: false,
	installed_on: "",
});

const isInstallDialogOpen = ref(false);

/** Install and Retry show loading until the dialog closes, in any way. */
const isAskingInstall = computed(() => working.value || isInstallDialogOpen.value);

/**
 * Stays on the page. A new install adds a row. Then `isInstalled` becomes true,
 * and the watch loads the row. A retry keeps its row. So this code reloads its details.
 */
const install = async () => {
	isInstallDialogOpen.value = false;
	working.value = true;
	try {
		await installFromHub(props.extension, details.value!.version);
		toast.success("Installing…");
		await activeInstallation.value?.reload();
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

/** Cancels a stuck install or removes a failed install. Neither made anything, so this asks nothing. */
const discardInstall = async () => {
	working.value = true;
	try {
		await uninstallExtension(props.extension);
		toast.success("Removed");
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

watch([() => props.extension, isInstalled], load, { immediate: true });

/** The install job ends in a background worker. A finished one changes the list, so reload this page with it. */
watch(
	() => installations.value.find((row) => row.name === props.extension)?.install_state,
	(state, before) => before === "Installing" && state !== before && load(),
);

const setEnabled = async (enabled: boolean) => {
	working.value = true;
	try {
		await setExtensionEnabled(props.extension, enabled);
		await load();
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};

/** The doctypes an extension made hold the site's data. So uninstalling keeps them, and the question says so. */
const uninstall = async () => {
	working.value = true;
	try {
		const message = "This removes it for everyone. Your site keeps any data it saved.";
		if (await confirm(message, `Uninstall ${details.value?.label}?`)) {
			const isFromHub = details.value?.source === "Hub";
			await uninstallExtension(props.extension);
			// the watch shows the Hub page. An extension with no Hub has no page to show
			if (!isFromHub) emit("back");
		}
	} catch (thrown) {
		toast.error((thrown as Error).message);
	} finally {
		working.value = false;
	}
};
</script>

<style scoped>
/* The panel is 300 pixels wide. So content that cannot wrap must scroll in
 * its own box. It must not make the column wider. */
.extension-readme :deep(pre),
.extension-readme :deep(table) {
	overflow-x: auto;
	display: block;
	max-width: 100%;
}
</style>
