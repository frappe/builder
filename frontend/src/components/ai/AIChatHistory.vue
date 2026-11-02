<template>
	<Dialog v-model="open" title="Chat history" size="lg">
		<template #default>
			<div class="space-y-3">
				<FormControl v-model="query" placeholder="Search chat titles" aria-label="Search chat titles" />
				<p v-if="error" role="alert" class="text-p-sm text-ink-red-5">{{ error }}</p>
				<div class="max-h-80 space-y-1 overflow-auto">
					<button
						v-for="row in rows"
						:key="row.name"
						class="block w-full rounded p-2 text-left hover:bg-surface-gray-2"
						@click="select(row.name)">
						{{ row.title || "Untitled chat" }}
					</button>
					<p v-if="!loading && !rows.length" class="text-p-sm text-ink-gray-5">No chats found.</p>
				</div>
				<Button v-if="more" :loading="loading" @click="load(true)">Load older chats</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog, FormControl, createResource } from "frappe-ui";
import { ref, watch } from "vue";
const props = defineProps<{ pageId: string }>();
const open = defineModel<boolean>({ default: false });
const emit = defineEmits<{ select: [id: string] }>();
const query = ref("");
const rows = ref<Array<{ name: string; title?: string }>>([]);
const loading = ref(false);
const error = ref("");
const more = ref(true);
let epoch = 0;

async function load(append = false) {
	const intent = ++epoch;
	loading.value = true;
	error.value = "";
	try {
		const result = await createResource({ url: "builder.ai.api.list_page_ai_sessions" }).submit({
			page_id: props.pageId,
			search: query.value,
			offset: append ? rows.value.length : 0,
			limit: 20,
		});
		if (intent !== epoch) return;
		rows.value = append ? [...rows.value, ...result] : result;
		more.value = result.length === 20;
	} catch {
		if (intent === epoch) error.value = "Could not load chats. Try again.";
	} finally {
		if (intent === epoch) loading.value = false;
	}
}
function select(id: string) {
	open.value = false;
	emit("select", id);
}
watch([open, query, () => props.pageId], () => {
	if (open.value) load();
	else epoch++;
});
</script>
