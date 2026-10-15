<template>
	<!--
		The consent prompt. Builder shows it, never the extension. An extension
		frame cannot show, read or answer it. `confirmations.ts` keeps a queue,
		so it asks one question at a time.
	-->
	<Dialog v-if="prompt" :modelValue="true" size="sm" bare @update:modelValue="deny">
		<div class="bg-surface-elevation-2 p-5">
			<DialogTitle as="h3" class="text-md-semibold text-ink-gray-9">
				{{ prompt.extension.label }} wants access
			</DialogTitle>

			<!-- the period is in the interpolation. A newline before a separate "."
					becomes a text node, and Prettier moves the markup -->
			<p class="pt-4 text-p-sm text-ink-gray-6">
				It is asking to
				<span class="font-semibold text-ink-gray-8">{{ prompt.act }}</span>
				<template v-if="prompt.act === 'remove field'">
					<strong>{{ prompt.detail }}</strong>
					from
				</template>
				<!-- the space in the interpolation: Vue drops a line break between elements -->
				<template v-else-if="prompt.act === 'change access'">{{ " of" }}</template>
				the doctype
				<span class="font-semibold text-ink-gray-8">{{ `${prompt.doctype}.` }}</span>
			</p>

			<div v-if="isDestructive" class="mt-4 rounded-4 bg-surface-red-1 p-3">
				<p class="text-p-sm text-ink-red-6">
					{{
						prompt.detail
							? "This removes the field from forms and collection data. Existing page bindings may need to be updated."
							: "This removes the doctype from your site."
					}}
				</p>
				<Checkbox v-model="understood" class="pt-3" :label="`I trust ${prompt.extension.label} with this.`" />
			</div>

			<div class="flex justify-end gap-2 pt-4">
				<Button variant="subtle" @click="deny">Deny</Button>
				<Button variant="solid" :disabled="!canAllow" @click="allow">Allow</Button>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import { answerPrompt, pendingPrompt } from "@/extensions/data/confirmations";
import { Button, Checkbox } from "frappe-ui";
import { DialogTitle } from "reka-ui";
import { computed, ref, watch } from "vue";

const prompt = computed(() => pendingPrompt.value);
const understood = ref(false);

// the user answers each question separately. If the tick stayed, one answer
// would approve an act that the user never saw
watch(prompt, () => (understood.value = false));

const isDestructive = computed(() => prompt.value?.act === "delete" || prompt.value?.act === "remove field");
const canAllow = computed(() => !isDestructive.value || understood.value);

const allow = () => answerPrompt(true);

/** The button, Escape and a click outside all count as no. */
const deny = () => answerPrompt(false);
</script>
