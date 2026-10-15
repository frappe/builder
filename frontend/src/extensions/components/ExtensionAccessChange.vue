<template>
	<!-- one quiet line. The roles show only when the user opens it -->
	<div class="pt-2">
		<button
			type="button"
			class="flex items-center gap-1 text-p-sm text-ink-gray-6 hover:text-ink-gray-8"
			:aria-expanded="isOpen"
			@click="isOpen = !isOpen">
			<span
				class="lucide-chevron-right size-3.5 transition-transform"
				:class="{ 'rotate-90': isOpen }"
				aria-hidden="true" />
			{{ count }} {{ count === 1 ? "role" : "roles" }} changed
		</button>
		<div v-if="isOpen" class="flex flex-col gap-1 pl-4.5 pt-1 text-p-sm text-ink-gray-6">
			<p v-if="access.added.length">Added: {{ access.added.join(", ") }}</p>
			<p v-if="access.removed.length">Removed: {{ access.removed.join(", ") }}</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AccessChange } from "@/extensions/data/confirmations";
import { computed, ref } from "vue";

const props = defineProps<{ access: AccessChange }>();
const isOpen = ref(false);
const count = computed(() => props.access.added.length + props.access.removed.length);
</script>
