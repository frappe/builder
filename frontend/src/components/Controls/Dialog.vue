<template>
	<Dialog v-bind="attrs" ref="dialogRef" @update:modelValue="emit('update:modelValue', $event)">
		<template v-for="(_, name) in $slots" :key="name" v-slot:[name]="slotData">
			<slot :name="name" v-bind="slotData"></slot>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";
import { ref, useAttrs, watch } from "vue";
import { useRoute } from "vue-router";

const attrs = useAttrs();
const emit = defineEmits(["update:modelValue", "close"]);

const route = useRoute();
const dialogRef = ref();

// close dialog on route change
watch(
	() => route.fullPath,
	() => {
		if (attrs.modelValue) {
			emit("update:modelValue", false);
		}
	},
);
</script>
