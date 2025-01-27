<template>
	<Dialog v-model="showDialog" :options="{ title }">
		<template #body-content>
			<div class="space-y-4">
				<p class="text-p-base text-gray-800" v-if="message" v-html="message" />
			</div>
		</template>
		<template #actions>
			<BuilderButton class="w-full" v-bind="primaryActionProps" />
		</template>
	</Dialog>
</template>

<script lang="ts" setup>
import Dialog from "@/components/Controls/Dialog.vue";
import { onMounted, ref } from "vue";

const props = defineProps(["title", "message", "onClick"]);
const showDialog = ref(true);
showDialog.value = true;
console.log("AlertDialog mounted");

onMounted(() => {
	console.log("AlertDialog mounted");
});

const hide = () => {
	showDialog.value = false;
};
const primaryActionProps = {
	label: "Ok",
	variant: "solid",
	onClick: () => {
		props.onClick();
		hide();
	},
};
</script>
