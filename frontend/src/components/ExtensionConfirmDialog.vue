<template>
	<!--
		The consent prompt, drawn by Builder and never by the extension. An
		extension frame cannot paint here, cannot read this, and cannot answer it.

		One instance for the whole editor: `confirmations.ts` queues requests so only one
		question stands at a time.
	-->
	<Dialog v-if="prompt" :modelValue="true" size="sm" @update:modelValue="deny">
		<template #body>
			<div class="bg-surface-elevation-2 p-5">
				<h3 class="text-md-semibold text-ink-gray-9">{{ prompt.extension.label }} wants access</h3>

				<!-- the period is part of the interpolation, not a node beside it: a
					newline between a closing tag and a bare "." becomes a text node, and
					the sentence reads "Contact ." Prettier reflows the markup, so the
					punctuation cannot live in the whitespace -->
				<p class="pt-4 text-p-sm text-ink-gray-6">
					It is asking to
					<span class="font-semibold text-ink-gray-8">{{ verbs }}</span>
					{{ object }}
					<span class="font-semibold text-ink-gray-8">{{ subject }}</span>
				</p>

				<p class="pt-2 text-p-sm text-ink-gray-5">
					{{ floor }}
				</p>

				<div v-if="prompt.sensitive" class="mt-4 rounded-4 bg-surface-red-1 p-3">
					<p v-if="prompt.kind === 'schema'" class="text-p-sm text-ink-red-6">
						Dropping a doctype drops its table and every record in it. Nothing here can undo that.
					</p>
					<p v-else class="text-p-sm text-ink-red-6">
						The script runs on the published page, for every visitor, and it can do anything this site's own
						pages can do. You can read it and remove it in the Code tab.
					</p>
					<label class="flex cursor-pointer items-start gap-2 pt-3 text-p-sm text-ink-red-6">
						<input v-model="understood" type="checkbox" class="mt-0.5" />
						<span>I understand, and I trust {{ prompt.extension.label }} with this.</span>
					</label>
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
import { Button } from "frappe-ui";
import { computed, ref, watch } from "vue";

const prompt = computed(() => pendingPrompt.value);
const understood = ref(false);

// each question is answered on its own. Carrying the tick over would let one
// consent stand for an act the user never saw
watch(prompt, () => (understood.value = false));

const canAllow = computed(() => !prompt.value?.sensitive || understood.value);

/** The subject and the full stop, so no reflow can put whitespace between them. */
const subject = computed(() => `${prompt.value?.subject}.`);

/** The one verb a schema or script prompt names. */
const verbs = computed(() => (prompt.value?.kind === "schema" ? (prompt.value.act ?? "") : "run a script"));

/** The one sentence that is true of every prompt: the user is still the ceiling. */
const floor = computed(
	() =>
		({
			schema: "It can only do what you can do. Changing a doctype needs your own System Manager role.",
			script: "It can only do what you can do. You can already add a script to this page by hand.",
		})[prompt.value?.kind ?? "script"],
);

/** What the verbs act on: the doctype itself, or a page. */
const object = computed(
	() => ({ schema: "the doctype", script: "on the page" })[prompt.value?.kind ?? "script"],
);

const allow = () => answerPrompt(true);

/**
 * The button, Escape and a click outside all mean the same thing. An unanswered
 * question is a no, which is what every browser permission prompt does.
 */
const deny = () => answerPrompt(false);
</script>
