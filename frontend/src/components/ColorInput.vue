<template>
	<ColorPicker :modelValue="value" @update:model-value="(color) => emit('change', color)">
		<template #target="{ togglePopover, isOpen }">
			<div class="relative mt-5">
				<div
					class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded"
					@click="togglePopover"
					:style="{
						backgroundColor: value,
					}"></div>
				<Input
					type="text"
					placeholder="Select Color"
					inputClass="pl-8"
					:value="value"
					@change="emit('change')"></Input>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { PropType, ref, watchEffect } from "vue";
import ColorPicker from "./ColorPicker.vue";

const props = defineProps({
	value: {
		type: String as PropType<HashString | null>,
		default: null,
	},
});

const emit = defineEmits(["change"]);
</script>
