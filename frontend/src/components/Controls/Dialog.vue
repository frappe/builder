<template>
	<Dialog v-bind="attrs" ref="dialogRef" @update:modelValue="toggleDialog" @close="toggleDialog">
		<template v-for="(_, name) in $slots" :key="name" v-slot:[name]="slotData">
			<slot :name="name" v-bind="slotData"></slot>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { confirm } from "@/utils/helpers";
import { useEventListener } from "@vueuse/core";
import { Dialog } from "frappe-ui";
import { ref, useAttrs } from "vue";
import { onBeforeRouteLeave } from "vue-router";

const attrs = useAttrs();
const emit = defineEmits(["update:modelValue", "close"]);

const dialogRef = ref();

// close dialog on route change
onBeforeRouteLeave((to, from, next) => {
	if (!attrs.modelValue) {
		next();
	} else {
		showConfirmationDialog().then((res) => {
			next(res);
		});
	}
});

let waitingForResponse = false;
const toggleDialog = (value: boolean) => {
	if (value) {
		emit("update:modelValue", value);
		return;
	}
	if (waitingForResponse) return;
	showConfirmationDialog();
};

useEventListener("beforeunload", (e) => {
	if (attrs?.isDirty) {
		e.preventDefault();
		e.returnValue = "You have unsaved changes. Please save before leaving.";
	}
});

const showConfirmationDialog = async () => {
	waitingForResponse = true;
	if (attrs.isDirty) {
		return await confirm("You have unsaved changes. Are you sure you want to leave?").then((res) => {
			if (res) {
				emit("update:modelValue", false);
			}
			waitingForResponse = false;
			return res;
		});
	} else {
		emit("update:modelValue", false);
	}
	waitingForResponse = false;
	return true;
};
</script>
