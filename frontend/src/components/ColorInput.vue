<template>
	<ColorPicker :modelValue="value" @update:modelValue="(color) => emit('change', color)">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
					<slot />
				</span>
				<div class="relative w-[150px]">
					<div
						class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
						@click="togglePopover"
						:style="{
							background: value ? value : `url(/color-circle.png) center / contain`,
						}"></div>
					<Input
						type="text"
						class="rounded-md text-sm text-gray-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:focus:bg-zinc-700"
						placeholder="Select Color"
						inputClass="pl-8 pr-6"
						:value="value"
						@change="(value: string) => emit('change', value)"></Input>
					<div
						class="absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
						@click="clearValue"
						v-show="value">
						<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24">
							<path
								fill="currentColor"
								d="M18.3 5.71a.996.996 0 0 0-1.41 0L12 10.59L7.11 5.7A.996.996 0 1 0 5.7 7.11L10.59 12L5.7 16.89a.996.996 0 1 0 1.41 1.41L12 13.41l4.89 4.89a.996.996 0 1 0 1.41-1.41L13.41 12l4.89-4.89c.38-.38.38-1.02 0-1.4z" />
						</svg>
					</div>
				</div>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { PropType } from "vue";
import ColorPicker from "./ColorPicker.vue";

defineProps({
	value: {
		type: String as PropType<StyleValue | null>,
		default: null,
	},
});

const emit = defineEmits(["change"]);

const clearValue = () => emit("change", null);
</script>
