<template>
	<div class="flex flex-col gap-3">
		<div @keydown.enter.prevent="pickFirst">
			<BuilderInput
				type="text"
				:autofocus="true"
				:modelValue="query"
				placeholder="Filter models"
				hideClearButton
				@input="(value: string) => (query = value)" />
		</div>
		<p v-if="!groups.length" class="text-p-sm text-ink-gray-5">No model matches “{{ query }}”.</p>
		<div v-for="group in groups" :key="group.provider" class="flex flex-col gap-0.5">
			<div
				class="flex items-center gap-2 border-b border-outline-gray-1 pb-1.5 text-xs font-medium text-ink-gray-5">
				{{ group.provider }}
				<AIProviderCredits v-if="group.reportsCredits" :provider="group.provider" />
			</div>
			<button
				v-for="model in group.models"
				:key="model.name"
				class="flex items-center gap-2 rounded-4 px-1.5 py-1.5 text-left hover:bg-surface-gray-2"
				@click="$emit('pick', model.name)">
				<span class="flex min-w-0 flex-1 flex-col">
					<span class="flex items-center gap-1.5">
						<span class="truncate text-sm text-ink-gray-8">{{ model.label }}</span>
						<span
							v-if="model.vision"
							class="lucide-eye size-3.5 shrink-0 text-ink-gray-4"
							title="Accepts images" />
					</span>
					<span v-if="model.ready === false" class="text-xs text-ink-amber-7">No API key</span>
				</span>
				<span v-if="model.name === selected" class="lucide-check size-4 shrink-0 text-ink-gray-7" />
			</button>
		</div>
		<button
			class="self-start text-xs text-ink-gray-5 underline underline-offset-2 hover:text-ink-gray-8"
			@click="$emit('manage')">
			Manage providers and models
		</button>
	</div>
</template>

<script setup lang="ts">
import AIProviderCredits from "@/components/ai/AIProviderCredits.vue";
import type { AIProvider } from "@/components/ai/types";
import { computed, ref } from "vue";

const props = defineProps<{ providers: AIProvider[]; selected: string; filter?: string }>();
const emit = defineEmits<{ pick: [name: string]; manage: [] }>();

const query = ref(props.filter || "");

const groups = computed(() => {
	const needle = query.value.trim().toLowerCase();
	return props.providers
		.map((group) => ({
			provider: group.provider,
			reportsCredits: group.models.some((m) => m.api_base),
			models: group.models.filter((m) => !needle || `${m.label} ${m.name}`.toLowerCase().includes(needle)),
		}))
		.filter((group) => group.models.length);
});

const pickFirst = () => {
	const first = groups.value[0]?.models[0];
	if (first) emit("pick", first.name);
};
</script>
