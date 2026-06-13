<template>
	<Dialog v-model="show" title="Version History" size="lg">
		<template #default>
			<div class="flex flex-col gap-4">
				<!-- Save a manual checkpoint -->
				<div class="flex items-end gap-2">
					<TextInput
						v-model="newLabel"
						type="text"
						label="Save current version"
						placeholder="Optional name (e.g. before redesign)"
						class="flex-1"
						@keydown.enter="saveVersion" />
					<Button
						variant="solid"
						icon-left="save"
						:loading="saving"
						label="Save Version"
						@click="saveVersion" />
				</div>

				<!-- Snapshot list -->
				<div class="flex max-h-[50vh] flex-col overflow-y-auto">
					<div
						v-if="!snapshots.data?.length && !snapshots.loading"
						class="py-10 text-center text-p-sm text-ink-gray-4">
						No saved versions yet. Versions are captured each time you publish, or when you save one manually.
					</div>
					<div
						v-for="snapshot in snapshots.data"
						:key="snapshot.name"
						class="flex items-center justify-between gap-3 border-b border-outline-gray-1 py-3 last:border-b-0">
						<div class="flex min-w-0 flex-col gap-1">
							<div class="flex items-center gap-2">
								<Badge
									:theme="snapshot.snapshot_type === 'Manual' ? 'blue' : 'green'"
									variant="subtle"
									:label="snapshot.snapshot_type || 'Snapshot'" />
								<span v-if="snapshot.label" class="truncate text-sm text-ink-gray-8">
									{{ snapshot.label }}
								</span>
							</div>
							<span class="text-xs text-ink-gray-5">
								{{ formatRelative(snapshot.creation) }} · {{ snapshot.owner }}
							</span>
						</div>
						<Button
							variant="subtle"
							icon-left="rotate-ccw"
							:loading="restoringName === snapshot.name"
							label="Restore"
							@click="restore(snapshot)" />
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import usePageStore from "@/stores/pageStore";
import { BuilderSnapshot } from "@/types/doctypes";
import { confirm } from "@/utils/helpers";
import { Badge, Button, createListResource, TextInput, toast } from "frappe-ui";
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

// (re)load the list whenever the dialog opens for the active page
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
