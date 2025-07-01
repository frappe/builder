<template>
	<div>
		<ColorPicker
			:modelValue="modelValue"
			@update:modelValue="
				(color) => {
					emit('update:modelValue', color);
				}
			">
			<template #target="{ togglePopover, isOpen }">
				<div class="flex items-center justify-between">
					<InputLabel v-if="label">{{ label }}</InputLabel>
					<div class="relative w-full">
						<BuilderInput
							type="text"
							class="[&>div>input]:pl-8"
							@focus="togglePopover"
							:placeholder="placeholder"
							:modelValue="modelValue"
							@update:modelValue="
								(val: string | null) => {
									const color = getRGB(val);
									emit('update:modelValue', color);
								}
							">
							<template #prefix>
								<div
									class="h-4 w-4 rounded shadow-sm"
									@click="togglePopover"
									:style="{
										background: modelValue
											? modelValue
											: `url(/assets/builder/images/color-circle.png) center / contain`,
									}"></div>
							</template>
						</BuilderInput>
					</div>
				</div>
			</template>
		</ColorPicker>
	</div>
</template>
<script setup lang="ts">
import { getRGB } from "@/utils/helpers";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

withDefaults(
	defineProps<{
		modelValue?: HashString | null;
		label?: string;
		placeholder?: string;
	}>(),
	{
		modelValue: null,
		placeholder: "Set Color",
	},
);

const emit = defineEmits(["update:modelValue"]);
</script>
