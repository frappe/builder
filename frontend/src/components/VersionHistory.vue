<template>
	<div class="flex h-full flex-col bg-surface-base">
		<!-- header -->
		<div class="flex items-center justify-between border-b border-outline-gray-2 px-3 py-2.5">
			<div class="flex items-center gap-1.5">
				<Button variant="ghost" size="sm" icon="lucide-chevron-left" @click="close" />
				<span class="text-base font-medium text-ink-gray-8">Version History</span>
			</div>
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-bookmark-plus"
				:loading="saving"
				tooltip="Save current version"
				@click="toggleSaveRow" />
		</div>

		<!-- name + save current version -->
		<div v-if="showSaveRow" class="flex items-center gap-2 border-b border-outline-gray-2 px-3 py-2.5">
			<TextInput
				ref="labelInput"
				v-model="newLabel"
				type="text"
				placeholder="Name this version (optional)"
				class="flex-1"
				@keydown.enter="saveVersion" />
			<Button variant="solid" size="sm" :loading="saving" label="Save" @click="saveVersion" />
		</div>

		<!-- list -->
		<div class="no-scrollbar flex-1 overflow-y-auto p-2">
			<div
				v-if="!snapshots.data?.length && !snapshots.loading"
				class="px-2 pt-10 text-center text-p-sm text-ink-gray-4">
				No saved versions yet. A version is captured every time you publish, or when you save one manually.
			</div>

			<template v-else>
				<!-- current (working draft) -->
				<button
					class="group flex w-full items-center gap-2.5 rounded px-3 py-2 text-left"
					:class="canvasStore.previewSnapshotName === null ? 'bg-surface-gray-3' : 'hover:bg-surface-gray-2'"
					@click="canvasStore.clearVersionPreview()">
					<span class="mt-1.5 h-2 w-2 shrink-0 self-start rounded-full bg-gray-400" />
					<div class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-p-sm font-medium text-ink-gray-8">Current version</span>
						<span class="truncate text-p-xs text-ink-gray-5">Working draft · unpublished changes</span>
					</div>
				</button>

				<!-- saved versions -->
				<button
					v-for="snapshot in snapshots.data"
					:key="snapshot.name"
					class="group flex w-full items-center gap-2.5 rounded px-3 py-2 text-left"
					:class="
						canvasStore.previewSnapshotName === snapshot.name
							? 'bg-surface-gray-3'
							: 'hover:bg-surface-gray-2'
					"
					@click="canvasStore.previewVersion(snapshot.name)">
					<span
						class="mt-1.5 h-2 w-2 shrink-0 self-start rounded-full"
						:class="snapshot.snapshot_type === 'Manual' ? 'bg-blue-500' : 'bg-green-500'" />
					<div class="flex min-w-0 flex-1 flex-col">
						<span class="truncate text-p-sm text-ink-gray-8">
							<template v-if="snapshot.label">{{ snapshot.label }}</template>
							<UseTimeAgo v-else v-slot="{ timeAgo }" :time="snapshot.creation">{{ timeAgo }}</UseTimeAgo>
						</span>
						<span class="truncate text-p-xs text-ink-gray-5">
							<UseTimeAgo v-if="snapshot.label" v-slot="{ timeAgo }" :time="snapshot.creation">
								{{ timeAgo }}
							</UseTimeAgo>
							<template v-else>{{ snapshot.snapshot_type || "Version" }}</template>
						</span>
					</div>
					<Button
						class="shrink-0 opacity-0 group-hover:opacity-100"
						:class="{ '!opacity-100': canvasStore.previewSnapshotName === snapshot.name }"
						variant="subtle"
						size="sm"
						icon="lucide-rotate-ccw"
						tooltip="Restore this version as your draft"
						:loading="restoringName === snapshot.name"
						@click.stop="restore(snapshot)" />
					<Avatar
						class="shrink-0"
						:shape="'circle'"
						:image="user(snapshot.owner).image"
						:label="user(snapshot.owner).fullname"
						size="sm"
						:title="user(snapshot.owner).fullname" />
				</button>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderSnapshot } from "@/types/doctypes";
import { getUserInfo } from "@/usersInfo";
import { confirm } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Avatar, Button, createListResource, TextInput, toast } from "frappe-ui";
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

const newLabel = ref("");
const saving = ref(false);
const showSaveRow = ref(false);
const restoringName = ref<string | null>(null);
const labelInput = ref<InstanceType<typeof TextInput> | null>(null);

const user = (email: string) => getUserInfo(email || "Administrator");

const snapshots = createListResource({
	doctype: "Builder Snapshot",
	fields: ["name", "label", "snapshot_type", "creation", "owner"],
	filters: {
		reference_doctype: "Builder Page",
		reference_name: pageStore.selectedPage as string,
	},
	orderBy: "creation desc",
	pageLength: 100,
	auto: true,
});

// reload for the active page (the panel can outlive a page switch)
watch(
	() => pageStore.selectedPage,
	(page) => {
		if (!page) return;
		snapshots.filters = { reference_doctype: "Builder Page", reference_name: page as string };
		snapshots.reload();
	},
);

// instantly refresh the list whenever a new version is created (publish or manual save)
watch(
	() => pageStore.snapshotsVersion,
	() => snapshots.reload(),
);

// closing the panel must always exit the preview (restores edit mode)
function close() {
	canvasStore.clearVersionPreview();
	builderStore.showVersionHistory = false;
}

// safety net: never leave a dangling read-only preview if unmounted any other way
onBeforeUnmount(() => canvasStore.clearVersionPreview());

function toggleSaveRow() {
	showSaveRow.value = !showSaveRow.value;
	if (showSaveRow.value) nextTick(() => labelInput.value?.el?.focus?.());
}

async function saveVersion() {
	if (saving.value) return;
	saving.value = true;
	try {
		await pageStore.createManualSnapshot(newLabel.value.trim() || undefined);
		newLabel.value = "";
		showSaveRow.value = false;
		await snapshots.reload();
		toast.success("Version saved");
	} finally {
		saving.value = false;
	}
}

async function restore(snapshot: BuilderSnapshot) {
	const confirmed = await confirm(
		"This will load this version into the editor as your current draft. Your live page won't change until you publish. Continue?",
	);
	if (!confirmed) return;
	restoringName.value = snapshot.name;
	try {
		await pageStore.restoreSnapshot(snapshot.name);
		// restoreSnapshot hard-reloads the editor, so nothing below runs in practice
	} finally {
		restoringName.value = null;
	}
}
</script>
