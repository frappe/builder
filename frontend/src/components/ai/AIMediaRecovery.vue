<template>
	<details class="mt-3 space-y-3">
		<summary class="cursor-pointer">Reconcile provider result</summary>
		<p>Check the provider account first. Recovery is available five minutes after the request.</p>
		<FormControl v-model="outcome" type="select" label="Verified outcome" :options="outcomes" />
		<FormControl v-model="evidence" type="textarea" label="Receipt or support confirmation" />
		<FormControl
			v-if="outcome === 'acquired'"
			v-model="fileUrl"
			label="Recovered original"
			placeholder="URL of the original uploaded to this page" />
		<p v-if="error" role="alert" class="text-ink-red-5">{{ error }}</p>
		<Button
			:loading="saving"
			:disabled="evidence.length < 10 || (outcome === 'acquired' && !fileUrl)"
			@click="resolve">
			Record verified result
		</Button>
	</details>
</template>
<script setup lang="ts">
import { Button, FormControl, call } from "frappe-ui";
import { ref } from "vue";
const props = defineProps<{ pageId: string; requestId: string }>();
const emit = defineEmits<{ resolved: [] }>();
const outcomes = [
	{ label: "Not charged", value: "not_charged" },
	{ label: "Acquired — recovered original uploaded", value: "acquired" },
	{ label: "Charged, no usable asset", value: "charged_without_asset" },
];
const outcome = ref("not_charged"),
	evidence = ref(""),
	fileUrl = ref(""),
	error = ref(""),
	saving = ref(false);
async function resolve() {
	saving.value = true;
	error.value = "";
	try {
		await call("builder.ai.media.reconcile_request", {
			page_id: props.pageId,
			request_id: props.requestId,
			outcome: outcome.value,
			evidence: evidence.value,
			file_url: fileUrl.value || null,
		});
		emit("resolved");
	} catch (exception: any) {
		error.value =
			exception.messages?.[0] || "Could not reconcile this request. Verify the receipt and try again.";
	} finally {
		saving.value = false;
	}
}
</script>
