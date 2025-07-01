<template>
	<ColorPicker :modelValue="value" @update:modelValue="(color) => emit('change', color)">
		<template #target="{ togglePopover, isOpen }">
			<div class="flex items-center justify-between">
				<InputLabel>{{ label }}</InputLabel>
				<div class="relative w-full">
					<BuilderInput
						type="text"
						class="[&>div>input]:pl-8"
						@focus="togglePopover"
						:placeholder="placeholder"
						:modelValue="value"
						@update:modelValue="
							(value: string | null) => {
								value = getRGB(value);
								emit('change', value);
							}
						">
						<template #prefix>
							<div
								class="h-4 w-4 rounded shadow-sm"
								@click="togglePopover"
								:style="{
									background: value ? value : `url(/assets/builder/images/color-circle.png) center / contain`,
								}"></div>
						</template>
					</BuilderInput>
				</div>
			</div>
		</template>
	</ColorPicker>
</template>
<script setup lang="ts">
import { getRGB } from "@/utils/helpers";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

withDefaults(
	defineProps<{
		value?: HashString | null;
		label?: string;
		placeholder?: string;
	}>(),
	{
		value: null,
		label: "",
		placeholder: "Set Color",
	},
);

const emit = defineEmits(["change"]);
</script>
