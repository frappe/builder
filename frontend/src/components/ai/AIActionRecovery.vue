<template>
	<div class="mt-2 space-y-3 rounded border border-outline-gray-2 p-3 text-p-sm">
		<p>
			This action has no confirmed result yet. If it was interrupted, check the actual page, settings or
			provider receipt before continuing.
		</p>
		<FormControl
			v-model="evidence"
			type="textarea"
			label="What did you verify?"
			placeholder="Describe the result and any receipt reference" />
		<p v-if="error" role="alert" class="text-ink-red-5">{{ error }}</p>
		<div class="flex gap-2">
			<Button :loading="saving" :disabled="evidence.length < 10" @click="resolve('applied')">
				Verified as applied
			</Button>
			<Button :disabled="saving || evidence.length < 10" @click="resolve('not_applied')">
				Verified as not applied
			</Button>
		</div>
		<p class="text-p-xs text-ink-gray-6">
			Available after five minutes. This records your check without repeating the action.
		</p>
	</div>
</template>
<script setup lang="ts">
import { Button, FormControl, call } from "frappe-ui";
import { ref } from "vue";
const props = defineProps<{ messageId: string }>();
const emit = defineEmits<{ resolved: [] }>();
const evidence = ref(""),
	saving = ref(false),
	error = ref("");
async function resolve(outcome: string) {
	saving.value = true;
	error.value = "";
	try {
		await call("builder.ai.api.reconcile_pending_action", {
			message_id: props.messageId,
			outcome,
			evidence: evidence.value,
		});
		emit("resolved");
	} catch (exception: any) {
		error.value =
			exception.messages?.[0] || "Could not reconcile this action yet. Check again after five minutes.";
	} finally {
		saving.value = false;
	}
}
</script>
