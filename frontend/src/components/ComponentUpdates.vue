<template>
	<Popover v-if="outdated.length" placement="bottom-end">
		<template #target="{ togglePopover }">
			<Tooltip text="Component updates available" :hoverDelay="0.6" arrow-class="mb-3">
				<button
					class="relative flex h-7 w-7 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-3"
					@click="togglePopover">
					<span class="lucide-arrow-up-circle h-4 w-4" aria-hidden="true" />
					<span
						class="pointer-events-none absolute -right-0.5 -top-0.5 grid h-3.5 min-w-3.5 place-items-center rounded-full bg-amber-100 px-0.5 text-[9px] font-medium text-amber-700">
						{{ outdated.length }}
					</span>
				</button>
			</Tooltip>
		</template>
		<template #body="{ close }">
			<div class="w-72 rounded-lg bg-surface-base p-3 shadow-xl">
				<div class="mb-2 flex items-center justify-between">
					<span class="text-sm font-medium text-ink-gray-8">Component updates</span>
					<Button variant="subtle" size="sm" label="Update all" :loading="updatingAll" @click="updateAll" />
				</div>
				<p class="mb-3 text-xs text-ink-gray-5">
					These components changed since this page was last updated. Update to use the latest.
				</p>
				<div class="flex max-h-72 flex-col overflow-y-auto">
					<div
						v-for="item in outdated"
						:key="item.component_id"
						class="flex items-center justify-between gap-2 border-b border-outline-gray-1 py-2 last:border-b-0">
						<div class="flex min-w-0 flex-col">
							<span class="truncate text-sm text-ink-gray-8">{{ item.component_name }}</span>
							<span class="text-xs text-ink-gray-5">
								{{ item.count }} instance{{ item.count === 1 ? "" : "s" }}
							</span>
						</div>
						<Button
							variant="ghost"
							size="sm"
							label="Update"
							:loading="updating === item.component_id"
							@click="update(item.component_id)" />
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup lang="ts">
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { Button, Popover, Tooltip } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";

const componentStore = useComponentStore();
const pageStore = usePageStore();
const canvasStore = useCanvasStore();

const updating = ref<string | null>(null);
const updatingAll = ref(false);

const outdated = computed(() => componentStore.getOutdatedComponentList());

async function update(componentId: string) {
	updating.value = componentId;
	try {
		await componentStore.updateComponentInstances(componentId);
	} finally {
		updating.value = null;
	}
}

async function updateAll() {
	updatingAll.value = true;
	try {
		await componentStore.updateAllOutdatedComponents();
	} finally {
		updatingAll.value = false;
	}
}

watch(
	() => pageStore.selectedPage,
	(page) => {
		if (page) componentStore.refreshComponentUpdates();
	},
	{ immediate: true },
);

watch(
	() => canvasStore.editingMode,
	(mode, prev) => {
		if (mode === "page" && prev && prev !== "page") {
			// wait for activeCanvas to swap back to the page canvas before walking it
			nextTick(() => componentStore.refreshComponentUpdates());
		}
	},
);
</script>
