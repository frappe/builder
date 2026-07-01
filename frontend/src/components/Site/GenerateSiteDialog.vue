<template>
	<Dialog v-model="show" :options="{ title: 'Build with AI', size: 'lg' }">
		<template #body-content>
			<p class="mb-3 text-p-sm text-ink-gray-6">
				Describe what you'd like — a whole website or just a change. I'll take it from there.
			</p>
			<FormControl
				ref="input"
				type="textarea"
				:rows="4"
				v-model="prompt"
				:placeholder="placeholder"
				@keydown.meta.enter="submit"
				@keydown.ctrl.enter="submit" />
			<div class="mt-2 flex flex-wrap gap-1.5">
				<button
					v-for="example in examples"
					:key="example"
					class="rounded-full border border-outline-gray-2 px-2.5 py-1 text-xs text-ink-gray-6 hover:bg-surface-gray-2"
					@click="prompt = example">
					{{ example }}
				</button>
			</div>
			<div class="mt-5 flex justify-end gap-2">
				<Button variant="subtle" @click="show = false">Cancel</Button>
				<Button variant="solid" :loading="submitting" :disabled="!prompt.trim()" @click="submit">
					Build it
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { useDashboardState } from "@/composables/useDashboardState";
import router from "@/router";
import { Dialog, FormControl, createResource, toast } from "frappe-ui";
import { computed, ref } from "vue";

const { showGenerateSiteDialog } = useDashboardState();
const show = computed({
	get: () => showGenerateSiteDialog.value,
	set: (v) => (showGenerateSiteDialog.value = v),
});

const prompt = ref("");
const submitting = ref(false);

const placeholder =
	"e.g. A site for my coffee roastery — story, menu, and a contact form. Or: add a pricing page.";
const examples = [
	"A portfolio site for a freelance photographer",
	"A landing page for a SaaS app with pricing",
	"A restaurant site with menu and reservations",
];

const generate = createResource({ url: "builder.ai.api.generate_site", method: "POST" });

async function submit() {
	const brief = prompt.value.trim();
	if (!brief || submitting.value) return;
	submitting.value = true;
	try {
		const res = await generate.submit({ prompt: brief });
		show.value = false;
		prompt.value = "";
		router.push({ name: "site-progress", params: { batchId: res.batch_id } });
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not start the build. Please try again.");
	} finally {
		submitting.value = false;
	}
}
</script>
