<template>
	<ColorPicker :modelValue="colorValue" @update:modelValue="(color) => emit('change', color)">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel>{{ label }}</InputLabel>
				<div class="relative w-full">
					<div
						class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
						@click="togglePopover"
						:style="{
							background: value ? value : `url(/assets/builder/images/color-circle.png) center / contain`,
						}"></div>
					<Input
						type="text"
						class="[&>div>input]:pl-8"
						placeholder="Set Color"
						:modelValue="value"
						@update:modelValue="
							(value: string | null) => {
								value = getRGB(value);
								emit('change', value);
							}
						" />
				</div>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { getRGB } from "@/utils/helpers";
import { PropType } from "vue";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

const props = defineProps({
	value: {
		type: String as PropType<StyleValue | null>,
		default: null,
	},
	label: {
		type: String,
		default: "",
	},
});

const colorValue = props.value as HashString;
const emit = defineEmits(["change"]);
</script>
