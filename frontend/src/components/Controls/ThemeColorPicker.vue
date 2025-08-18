<template>
	<Popover :placement="placement" class="!block w-full" popoverClass="!min-w-fit !mr-[30px]">
		<template #target="{ togglePopover, isOpen }">
			<slot name="target" :togglePopover="togglePopover" :isOpen="isOpen"></slot>
		</template>
		<template #body="{ close, isOpen }">
			<div class="flex flex-col gap-3 rounded-lg bg-surface-white p-4 shadow-lg">
				<div class="flex items-center justify-between">
					<h4 class="text-sm font-medium text-ink-gray-9">Set Color</h4>
					<button @click="close" class="text-ink-gray-6 hover:text-ink-gray-9">
						<FeatherIcon name="x" class="size-4" />
					</button>
				</div>

				<OptionToggle
					:modelValue="activeMode"
					:options="[
						{ label: 'Light', value: 'light', icon: 'sun' },
						{ label: 'Dark', value: 'dark', icon: 'moon' },
					]"
					@update:modelValue="switchMode" />
				<ColorPicker
					v-if="isOpen"
					ref="colorPickerRef"
					renderMode="inline"
					:modelValue="activeMode === 'light' ? props.lightValue : props.darkValue"
					:showInput="true"
					placement="left"
					@update:modelValue="updateActiveColor"></ColorPicker>
			</div>
		</template>
	</Popover>
</template>

<script setup lang="ts">
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import { useDark } from "@vueuse/core";
import { FeatherIcon, Popover } from "frappe-ui";
import { ref } from "vue";

const colorPickerRef = ref();

const props = withDefaults(
	defineProps<{
		lightValue?: string | null;
		darkValue?: string | null;
		placement?: string;
	}>(),
	{
		lightValue: null,
		darkValue: null,
		placement: "bottom-start",
	},
);

const emit = defineEmits<{
	"update:lightValue": [value: string | null];
	"update:darkValue": [value: string | null];
}>();

const isDark = useDark({
	attribute: "data-theme",
});

const activeMode = ref<"light" | "dark">(isDark.value ? "dark" : "light");

const updateActiveColor = (color: string | null) => {
	if (activeMode.value === "light") {
		emit("update:lightValue", color);
	} else {
		emit("update:darkValue", color);
	}
};

const switchMode = (mode: "light" | "dark") => {
	activeMode.value = mode;
};
</script>
