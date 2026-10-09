<template>
	<span v-if="credits" class="ml-auto shrink-0 whitespace-nowrap text-p-xs text-ink-gray-6" :title="spent">
		{{ money(credits.balance) }} left
	</span>
</template>

<script setup lang="ts">
import { createResource } from "frappe-ui";
import { computed, ref } from "vue";

type Credits = { balance: number; spent: number | null };

const props = defineProps<{ provider: string }>();

const credits = ref<Credits | null>(null);

createResource({
	url: "builder.ai.api.get_provider_credits",
	params: { provider: props.provider },
	auto: true,
	onSuccess(res: Credits | null | undefined) {
		credits.value = res ?? null;
	},
});

const money = (value: number) => `$${value.toFixed(2)}`;

const spent = computed(() =>
	credits.value?.spent != null ? `${money(credits.value.spent)} spent` : undefined,
);
</script>
