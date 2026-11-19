<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center gap-1">
			<span class="text-sm-medium text-ink-gray-6">{{ __("Models") }}</span>
			<span class="text-sm text-ink-gray-5">{{ models.length }}</span>
			<Button
				class="ml-auto"
				variant="ghost"
				size="sm"
				icon="lucide-refresh-cw"
				:tooltip="__('Check for New Models')"
				:aria-label="__('Check for New Models')"
				:loading="isChecking"
				@click="checkForModels" />
		</div>

		<BuilderInput
			v-if="models.length > PREVIEW"
			type="text"
			icon-left="lucide-search"
			:placeholder="__('Search models')"
			:model-value="query"
			@input="(value: string) => (query = value)" />

		<!-- the pane scrolls, so the list never does: a long list shows its first models and a "Show all" -->
		<div
			v-if="shownModels.length"
			class="flex flex-col divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
			<label
				v-for="model in shownModels"
				:key="model.name"
				class="flex cursor-pointer items-center gap-3 px-3 py-2">
				<div class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-p-sm text-ink-gray-8">{{ model.label || model.model_id }}</span>
					<span v-if="model.label" class="truncate text-p-xs text-ink-gray-5">{{ model.model_id }}</span>
				</div>
				<Switch
					size="sm"
					:model-value="Boolean(model.enabled)"
					@update:model-value="(on: boolean) => toggle(model.name, on)" />
			</label>
		</div>
		<p v-else-if="query.trim()" class="text-p-sm text-ink-gray-5">
			{{ __('No models match "{0}"', [query.trim()]) }}
		</p>
		<p v-else class="text-p-sm text-ink-gray-5">{{ __("No models yet.") }}</p>

		<div class="-ml-2 flex items-center gap-1">
			<Combobox
				:key="pickerKey"
				:options="addable"
				:placeholder="__('Search models')"
				@update:open="(open: boolean) => open && loadAddable()"
				@update:model-value="add">
				<template #trigger>
					<Button variant="ghost" size="sm" icon-left="lucide-plus" :label="__('Add Model')" />
				</template>
			</Combobox>
			<Button
				v-if="models.length > PREVIEW && !query.trim()"
				class="ml-auto"
				variant="ghost"
				size="sm"
				:label="isShowingAll ? __('Show Fewer') : __('Show All {0}', [models.length])"
				@click="isShowingAll = !isShowingAll" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { api } from "@/components/ai/commands/shared";
import type { AddableModel } from "@/components/ai/types";
import { listedModelsOf, setModelEnabled, syncProviderModels } from "@/data/aiModels";
import { __ } from "@/translation";
import { Button, Combobox, Switch, toast } from "frappe-ui";
import { computed, ref } from "vue";

const PREVIEW = 6;

const props = defineProps<{ provider: string }>();
const emit = defineEmits<{ changed: [] }>();

const models = computed(() => listedModelsOf(props.provider));
const isShowingAll = ref(false);
const query = ref("");
// a search shows every match, past the first few
const shownModels = computed(() => {
	const needle = query.value.trim().toLowerCase();
	if (needle) return models.value.filter((m) => `${m.label} ${m.model_id}`.toLowerCase().includes(needle));
	return isShowingAll.value ? models.value : models.value.slice(0, PREVIEW);
});

const toggle = async (name: string, on: boolean) => {
	await setModelEnabled(name, on);
	emit("changed");
};

const isChecking = ref(false);
const checkForModels = async () => {
	isChecking.value = true;
	try {
		await syncProviderModels(props.provider);
		emit("changed");
		toast.success(__("Models are up to date"));
	} finally {
		isChecking.value = false;
	}
};

// everything the provider serves that is not listed yet, newest first
const addable = ref<{ label: string; value: string }[]>([]);
const pickerKey = ref(0);
const loadAddable = async () => {
	if (addable.value.length) return;
	const found = await api<AddableModel[]>("builder.ai.api.get_addable_models", { provider: props.provider });
	addable.value = found.map((m) => ({ label: m.label, value: m.model_id }));
};

const add = async (modelId: unknown) => {
	if (typeof modelId !== "string" || !modelId) return;
	const added = await api<{ label: string }>("builder.ai.api.add_ai_model", {
		provider: props.provider,
		model_id: modelId,
	});
	addable.value = addable.value.filter((m) => m.value !== modelId);
	// a fresh picker, so the next pick starts empty
	pickerKey.value++;
	toast.success(__("Added {0}", [added.label]));
	emit("changed");
};
</script>
