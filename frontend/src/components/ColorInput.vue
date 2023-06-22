<template>
	<ColorPicker :modelValue="value" @update:model-value="(color) => emit('change', color)">
		<template #target="{ togglePopover, isOpen }">
			<div class="mt-5 flex items-center justify-between">
				<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
					<slot />
				</span>
				<div class="relative w-[150px]">
					<div
						class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded"
						@click="togglePopover"
						:style="{
							background: value ? value : `url(/color-circle.png) center / contain`,
						}"></div>
					<Input
						type="text"
						placeholder="Select Color"
						inputClass="pl-8"
						:value="value"
						@change="emit('change')"></Input>
				</div>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { PropType } from "vue";
import ColorPicker from "./ColorPicker.vue";

const props = defineProps({
	value: {
		type: String as PropType<HashString | null>,
		default: null,
	},
});

const emit = defineEmits(["change"]);
</script>
