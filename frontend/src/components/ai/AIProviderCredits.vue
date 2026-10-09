<template>
	<span
		v-if="credits"
		class="ml-auto shrink-0 whitespace-nowrap text-p-xs text-ink-gray-6"
		:title="detailed ? undefined : spent">
		{{ money(credits.balance) }} left
		<template v-if="detailed && spent">· {{ spent }}</template>
	</span>
	<span v-else-if="detailed && loaded" class="ml-auto text-p-xs text-ink-gray-4">No balance reported</span>
</template>

<script setup lang="ts">
import { createResource } from "frappe-ui";
import { computed, ref } from "vue";

type Credits = { balance: number; spent: number | null };

const props = defineProps<{ provider: string; detailed?: boolean }>();

const credits = ref<Credits | null>(null);
const loaded = ref(false);

createResource({
	url: "builder.ai.api.get_provider_credits",
	params: { provider: props.provider },
	auto: true,
	onSuccess(res: Credits | null | undefined) {
		credits.value = res ?? null;
		loaded.value = true;
	},
	onError() {
		loaded.value = true;
	},
});

const money = (value: number) => `$${value.toFixed(2)}`;

const spent = computed(() =>
	credits.value?.spent != null ? `${money(credits.value.spent)} spent` : undefined,
);
</script>
