<template>
	<div class="space-y-3 text-p-sm">
		<p>
			Media reservation budget: ${{ budget }}. Reservations are conservative estimates; the provider's bill is
			authoritative.
		</p>
		<p v-if="!requests.length" class="text-ink-gray-6">No paid media requests recorded for this page.</p>
		<div v-for="request in requests" :key="request.id" class="rounded border border-outline-gray-2 p-3">
			<p>{{ request.label }} · {{ request.status }} · ${{ request.reserved_usd }} reserved</p>
			<p
				v-if="request.actual_cost_usd === null || request.actual_cost_usd === undefined"
				class="text-ink-gray-6">
				Actual charge not reported.
			</p>
			<p v-if="request.status === 'pending'" class="text-ink-orange-5">
				This request may have been charged. An administrator must reconcile its provider receipt before
				retrying.
			</p>
			<p v-if="request.reconciliation">
				{{ request.reconciliation.outcome }}: {{ request.reconciliation.evidence }}
			</p>
			<AIMediaRecovery
				v-if="request.status === 'pending' && canReconcile"
				:page-id="pageId"
				:request-id="request.id"
				@resolved="$emit('resolved')" />
		</div>
	</div>
</template>
<script setup lang="ts">
import AIMediaRecovery from "./AIMediaRecovery.vue";
defineProps<{
	pageId: string;
	canReconcile: boolean;
	budget: number | string;
	requests: Array<Record<string, any>>;
}>();
defineEmits<{ resolved: [] }>();
</script>
