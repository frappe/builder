<template>
	<div
		v-if="modelValue"
		class="pointer-events-none flex flex-col gap-0 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
		<button
			type="button"
			class="circle-cursor duration-250 -mb-[1.5px] flex h-3 w-5 items-center justify-center rounded transition-all ease-in-out active:-translate-y-[2px]"
			@click.stop="$emit('increment')"
			@mousedown.prevent
			tabindex="-1">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="text-ink-gray-6">
				<polyline points="18 15 12 9 6 15"></polyline>
			</svg>
		</button>
		<button
			type="button"
			class="circle-cursor duration-250 -mt-[1.5px] flex h-3 w-5 items-center justify-center rounded transition-all ease-in-out active:translate-y-[2px]"
			@click.stop="$emit('decrement')"
			@mousedown.prevent
			tabindex="-1">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="12"
				height="12"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				class="text-ink-gray-6">
				<polyline points="6 9 12 15 18 9"></polyline>
			</svg>
		</button>
	</div>
</template>

<script lang="ts" setup>
defineProps<{
	modelValue: boolean;
}>();

defineEmits(["increment", "decrement"]);
</script>

<style scoped>
.circle-cursor {
	cursor:
		url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12'%3E%3Ccircle cx='6' cy='6' r='5' fill='none' stroke='gray' stroke-width='1.5'/%3E%3C/svg%3E")
			6 6,
		auto;
}
</style>
