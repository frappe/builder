<template>
	<div>
		<ColorPicker
			:placement="placement"
			@open="events.onFocus"
			@close="handleClose"
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
							v-bind="events"
							ref="colorInput"
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
import { ref, useAttrs } from "vue";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const colorInput = ref<HTMLInputElement | null>(null);

withDefaults(
	defineProps<{
		modelValue?: HashString | null;
		label?: string;
		placeholder?: string;
		placement?: string;
	}>(),
	{
		modelValue: null,
		placeholder: "Set Color",
		placement: "left",
	},
);

const emit = defineEmits(["update:modelValue"]);

const handleClose = () => {
	if (colorInput.value && typeof colorInput.value.blur === "function") {
		colorInput.value.blur();
	}
	if (typeof events.onBlur === "function") {
		events.onBlur();
	}
};
</script>
