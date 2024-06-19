<template>
	<!-- prettier-ignore -->
	<ColorPicker :modelValue="(value as HashString)" @update:modelValue="(color) => emit('change', color)">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel>{{ label}}</InputLabel>
				<div class="relative w-full">
					<div
						class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
						@click="togglePopover"
						:style="{
							background: value ? value : `url(/assets/builder/images/color-circle.png) center / contain`,
						}"></div>
					<Input
						type="text"
						class="rounded-md [&>div>input]:pl-8 text-sm text-gray-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:focus:bg-zinc-700"
						placeholder="Set Color"
						:value="value"
						@change="
							(value: string | null) => {
								value = getRGB(value);
								emit('change', value);
							}
						" />
					<div
						class="absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
						@click="clearValue"
						v-show="value">
						<CrossIcon />
					</div>
				</div>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { getRGB } from "@/utils/helpers";
import { PropType } from "vue";
import ColorPicker from "./ColorPicker.vue";
import CrossIcon from "./Icons/Cross.vue";
import Input from "./Input.vue";
import InputLabel from "./InputLabel.vue";

defineProps({
	value: {
		type: String as PropType<StyleValue | null>,
		default: null,
	},
	label: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["change"]);

const clearValue = () => emit("change", null);
</script>
