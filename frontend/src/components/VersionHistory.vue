<template>
	<Transition
		enter-active-class="transition-transform duration-200 ease-out"
		leave-active-class="transition-transform duration-150 ease-in"
		enter-from-class="translate-x-full"
		leave-to-class="translate-x-full">
		<div
			v-if="show"
			class="bg-surface-base absolute bottom-0 right-0 top-[var(--toolbar-height)] z-10 flex w-72 flex-col border-l border-outline-gray-2 shadow-xl">
			<!-- header -->
			<div class="flex items-center justify-between px-4 py-3">
				<span class="text-base font-medium text-ink-gray-8">Version History</span>
				<button
					class="grid h-6 w-6 place-items-center rounded text-ink-gray-6 hover:bg-surface-gray-3"
					@click="show = false">
					<span class="lucide-x h-4 w-4" aria-hidden="true" />
				</button>
			</div>

			<!-- save current version -->
			<div class="flex items-center gap-2 px-4 pb-3">
				<TextInput
					v-model="newLabel"
					type="text"
					placeholder="Name this version (optional)"
					class="flex-1"
					@keydown.enter="saveVersion" />
				<Button variant="solid" :loading="saving" label="Save" @click="saveVersion" />
			</div>

			<!-- timeline -->
			<div class="relative flex-1 overflow-y-auto px-3 pb-4">
				<div
					v-if="!snapshots.data?.length && !snapshots.loading"
					class="px-1 pt-10 text-center text-p-sm text-ink-gray-4">
					No saved versions yet. A version is captured every time you publish, or when you save one manually.
				</div>

				<template v-else>
					<!-- vertical line -->
					<div class="bg-outline-gray-2 pointer-events-none absolute bottom-3 left-[15px] top-3 w-px" />

					<!-- current (live) marker -->
					<div class="relative flex items-center gap-3 py-2 pl-7 pr-1">
						<span
							class="bg-ink-gray-8 ring-surface-base absolute left-[9px] top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full ring-4" />
						<div class="flex min-w-0 flex-1 flex-col">
							<span class="text-p-sm font-medium text-ink-gray-8">Current version</span>
							<span class="text-p-xs text-ink-gray-5">Live · unsaved edits</span>
						</div>
						<Avatar
							:shape="'circle'"
							:image="user(activePageOwner).image"
							:label="user(activePageOwner).fullname"
							size="sm" />
					</div>

					<!-- saved versions -->
					<button
						v-for="snapshot in snapshots.data"
						:key="snapshot.name"
						class="group relative flex w-full items-center gap-3 rounded py-2 pl-7 pr-1 text-left hover:bg-surface-gray-2"
						:title="`Restore this version as a draft`"
						@click="restore(snapshot)">
						<span
							class="ring-surface-base absolute left-[9px] top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full ring-4"
							:class="snapshot.snapshot_type === 'Manual' ? 'bg-blue-500' : 'bg-green-500'" />
						<div class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-p-sm text-ink-gray-8">
								{{ snapshot.label || formatRelative(snapshot.creation) }}
							</span>
							<span class="truncate text-p-xs text-ink-gray-5">
								{{ snapshot.label ? formatRelative(snapshot.creation) : snapshot.snapshot_type || "Version" }}
							</span>
						</div>
						<span
							v-if="restoringName === snapshot.name"
							class="lucide-loader-circle h-4 w-4 animate-spin text-ink-gray-5" />
						<Avatar
							v-else
							:shape="'circle'"
							:image="user(snapshot.owner).image"
							:label="user(snapshot.owner).fullname"
							size="sm"
							:title="user(snapshot.owner).fullname" />
					</button>
				</template>
			</div>
		</div>
	</Transition>
</template>

<script setup lang="ts">
import usePageStore from "@/stores/pageStore";
import { BuilderSnapshot } from "@/types/doctypes";
import { getUserInfo } from "@/usersInfo";
import { confirm } from "@/utils/helpers";
import { Avatar, Button, createListResource, TextInput, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ (e: "update:modelValue", value: boolean): void }>();

const pageStore = usePageStore();

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

const newLabel = ref("");
const saving = ref(false);
const restoringName = ref<string | null>(null);

const user = (email: string) => getUserInfo(email || "Administrator");
const activePageOwner = computed(() => pageStore.activePage?.owner || "Administrator");

const snapshots = createListResource({
	doctype: "Builder Snapshot",
	fields: ["name", "label", "snapshot_type", "creation", "owner"],
	filters: {
		reference_doctype: "Builder Page",
		reference_name: pageStore.selectedPage as string,
	},
	orderBy: "creation desc",
	pageLength: 100,
});

// (re)load the list whenever the panel opens for the active page
watch(
	() => [props.modelValue, pageStore.selectedPage],
	([visible]) => {
		if (visible && pageStore.selectedPage) {
			snapshots.filters = {
				reference_doctype: "Builder Page",
				reference_name: pageStore.selectedPage as string,
			};
			snapshots.reload();
		}
	},
);

async function saveVersion() {
	if (saving.value) return;
	saving.value = true;
	try {
		await pageStore.createManualSnapshot(newLabel.value.trim() || undefined);
		newLabel.value = "";
		await snapshots.reload();
		toast.success("Version saved");
	} finally {
		saving.value = false;
	}
}

async function restore(snapshot: BuilderSnapshot) {
	const confirmed = await confirm(
		"This will load this version into the editor as your current draft for review. Your live page won't change until you publish. Continue?",
	);
	if (!confirmed) return;
	restoringName.value = snapshot.name;
	try {
		await pageStore.restoreSnapshot(snapshot.name);
		toast.success("Version restored as draft");
		show.value = false;
	} finally {
		restoringName.value = null;
	}
}

function formatRelative(timestamp: string) {
	const date = new Date(timestamp.replace(" ", "T"));
	const seconds = Math.round((Date.now() - date.getTime()) / 1000);
	const units: [number, Intl.RelativeTimeFormatUnit][] = [
		[60, "second"],
		[3600, "minute"],
		[86400, "hour"],
		[604800, "day"],
		[2592000, "week"],
		[31536000, "month"],
		[Infinity, "year"],
	];
	const divisors = [1, 60, 3600, 86400, 604800, 2592000, 31536000];
	const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
	for (let i = 0; i < units.length; i++) {
		if (seconds < units[i][0]) {
			return formatter.format(-Math.round(seconds / divisors[i]), units[i][1]);
		}
	}
	return date.toLocaleDateString();
}
</script>
