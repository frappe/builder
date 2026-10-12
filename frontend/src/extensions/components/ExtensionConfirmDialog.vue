<template>
	<!--
		The consent prompt. Builder shows it, never the extension. An extension
		frame cannot show, read or answer it. `confirmations.ts` keeps a queue,
		so it asks one question at a time.
	-->
	<Dialog v-if="prompt" :modelValue="true" size="sm" @update:modelValue="deny">
		<template #body>
			<div class="bg-surface-elevation-2 p-5">
				<h3 class="text-md-semibold text-ink-gray-9">{{ prompt.extension.label }} wants access</h3>

				<!-- the period is in the interpolation. A newline before a separate "."
					becomes a text node, and Prettier moves the markup -->
				<p class="pt-4 text-p-sm text-ink-gray-6">
					It is asking to
					<span class="font-semibold text-ink-gray-8">{{ prompt.act }}</span>
					the doctype
					<span class="font-semibold text-ink-gray-8">{{ `${prompt.doctype}.` }}</span>
				</p>

				<p class="pt-2 text-p-sm text-ink-gray-5">
					It can only do what you can do. Changing a doctype needs your own System Manager role.
				</p>

				<div v-if="isDelete" class="mt-4 rounded-4 bg-surface-red-1 p-3">
					<p class="text-p-sm text-ink-red-6">
						Dropping a doctype drops its table and every record in it. Nothing here can undo that.
					</p>
					<Checkbox
						v-model="understood"
						class="pt-3"
						:label="`I understand, and I trust ${prompt.extension.label} with this.`" />
				</div>

				<div class="flex justify-end gap-2 pt-4">
					<Button variant="subtle" @click="deny">Deny</Button>
					<Button variant="solid" :disabled="!canAllow" @click="allow">Allow</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { answerPrompt, pendingPrompt } from "@/extensions/data/confirmations";
import { Button, Checkbox } from "frappe-ui";
import { computed, ref, watch } from "vue";

const prompt = computed(() => pendingPrompt.value);
const understood = ref(false);

// the user answers each question separately. If the tick stayed, one answer
// would approve an act that the user never saw
watch(prompt, () => (understood.value = false));

const isDelete = computed(() => prompt.value?.act === "delete");
const canAllow = computed(() => !isDelete.value || understood.value);

const allow = () => answerPrompt(true);

/** The button, Escape and a click outside all count as no. */
const deny = () => answerPrompt(false);
</script>
