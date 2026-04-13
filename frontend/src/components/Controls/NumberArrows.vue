<template>
	<div
		v-if="modelValue && !disabled"
		class="pointer-events-none absolute right-5 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-0 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
		<button
			type="button"
			class="duration-250 flex h-3 w-5 items-center justify-center rounded transition-all ease-in-out active:-translate-y-[2px]"
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
			class="duration-250 -mt-[2px] flex h-3 w-5 items-center justify-center rounded transition-all ease-in-out active:translate-y-[2px]"
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
	modelValue: boolean; // this is hasNumber
	disabled?: boolean;
}>();

defineEmits(["increment", "decrement"]);
</script>
