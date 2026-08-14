<template>
	<div class="flex h-full min-h-0 flex-col gap-3">
		<div class="flex items-center justify-between">
			<div class="flex flex-col gap-1">
				<h3 class="text-p-base font-medium text-ink-gray-9">Models</h3>
				<p class="text-p-sm text-ink-gray-5">The chat's model picker offers every enabled model.</p>
			</div>
			<div class="flex gap-2">
				<Button size="sm" variant="subtle" iconLeft="lucide-server" @click="$emit('add-provider')">
					Add provider
				</Button>
				<Button size="sm" variant="solid" iconLeft="lucide-plus" @click="editModel(null)">Add model</Button>
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto pb-16">
			<div v-if="loadError" class="rounded bg-surface-red-1 p-3 text-p-sm text-ink-red-6">
				Could not load models: {{ loadError }}
			</div>
			<div
				v-else-if="!grouped.length"
				class="flex flex-col items-center gap-1 rounded border border-dashed border-outline-gray-2 py-8">
				<p class="text-p-sm text-ink-gray-7">No providers yet</p>
				<p class="text-p-xs text-ink-gray-5">
					Run bench migrate to get the shipped shortlist, or add a provider.
				</p>
			</div>

			<div v-for="group in grouped" :key="group.provider" class="flex flex-col">
				<button
					class="group/provider flex items-center gap-2 border-b border-outline-gray-1 py-1.5 text-left"
					@click="editProvider(group.provider)">
					<span
						class="text-p-sm font-medium"
						:class="group.enabled ? 'text-ink-gray-7' : 'text-ink-gray-4 line-through'">
						{{ group.label }}
					</span>
					<span v-if="group.hint" class="text-p-xs text-ink-gray-5">{{ group.hint }}</span>
					<span class="lucide-settings size-3.5 text-ink-gray-4 opacity-0 group-hover/provider:opacity-100" />
				</button>

				<div
					v-for="row in group.models"
					:key="row.name"
					class="group/row flex items-center gap-3 border-b border-outline-gray-1 py-2">
					<Switch
						size="sm"
						:modelValue="Boolean(row.enabled)"
						@update:modelValue="(value: boolean) => toggle(row, value)" />
					<button class="flex min-w-0 flex-1 flex-col text-left" @click="editModel(row)">
						<span class="flex items-center gap-1.5">
							<span class="truncate text-p-sm text-ink-gray-8">{{ row.label }}</span>
							<span
								v-if="row.supports_vision"
								class="lucide-eye size-3.5 text-ink-gray-4"
								title="Accepts images" />
						</span>
						<span class="truncate text-p-xs text-ink-gray-5">{{ row.name }}</span>
					</button>
					<Button
						size="sm"
						variant="ghost"
						icon="lucide-trash-2"
						class="opacity-0 group-hover/row:opacity-100"
						@click="remove(row)" />
				</div>
			</div>
		</div>

		<AIModelDialog v-model="showModelDialog" :model="activeModel" @saved="reload" />
		<AIProviderDialog v-model="showProviderDialog" :providerName="activeProvider" @saved="reload" />
	</div>
</template>

<script setup lang="ts">
import AIModelDialog from "@/components/Modals/AIModelDialog.vue";
import AIProviderDialog from "@/components/Modals/AIProviderDialog.vue";
import { aiModels, aiProviders, reloadAIRegistry } from "@/data/aiModels";
import { BuilderAIModel } from "@/types/doctypes";
import { Button, Switch } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

defineEmits(["add-provider"]);

const showModelDialog = ref(false);
const showProviderDialog = ref(false);
const activeModel = ref<BuilderAIModel | null>(null);
const activeProvider = ref<string | null>(null);

const grouped = computed(() =>
	(aiProviders.data || []).map((provider: any) => ({
		provider: provider.name,
		label: provider.provider_name,
		enabled: provider.enabled,
		// Only the base URL says anything the name doesn't: route_prefix is a slug of
		// that same name, so it rendered as "OpenRouter openrouter".
		hint: provider.api_base,
		models: (aiModels.data || []).filter((m: any) => m.provider === provider.name),
	})),
);

const editModel = (row: BuilderAIModel | null) => {
	activeModel.value = row;
	showModelDialog.value = true;
};

const editProvider = (name: string | null) => {
	activeProvider.value = name;
	showProviderDialog.value = true;
};

const loadError = ref("");

const reload = async () => {
	try {
		await reloadAIRegistry();
		loadError.value = "";
	} catch (error) {
		// An unmigrated site has no doctypes: say so instead of showing an empty list.
		loadError.value = (error as Error).message || "unknown error";
	}
};

const toggle = async (row: BuilderAIModel, enabled: boolean) => {
	await aiModels.setValue.submit({ name: row.name, enabled: enabled ? 1 : 0 });
	reload();
};

const remove = async (row: BuilderAIModel) => {
	await aiModels.delete.submit(row.name);
	reload();
};

onMounted(reload);
</script>
