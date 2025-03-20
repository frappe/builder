<template>
	<Switch
		v-model="value"
		class="[&>button>span]:bg-surface-gray-1 [&>span>[id^=headlessui-description]]:text-ink-gray-5 [&>span>[id^=headlessui-label]]:text-ink-gray-9"
		:class="{
			'[&>button]:bg-surface-gray-3 hover:[&>button]:!bg-surface-gray-4': !value,
			'[&>button]:bg-surface-gray-6 hover:[&>button]:!bg-surface-gray-5': value,
		}" />
</template>
<script setup lang="ts">
import { useVModel } from "@vueuse/core";
import { Switch } from "frappe-ui";

const props = defineProps<{
	modelValue: boolean;
}>();
const emit = defineEmits(["update:modelValue"]);
const value = useVModel(props, "modelValue", emit);
</script>
