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

			<!-- spaces and the period are in interpolations. Vue drops a line break
					between elements, and Prettier moves a separate "." -->
			<p class="pt-4 text-p-sm text-ink-gray-6">
				It wants to {{ actPhrases[prompt.act] }}
				<template v-if="prompt.detail">
					<strong class="text-ink-gray-8">{{ prompt.detail }}</strong>
					{{ " from " }}
				</template>
				<strong class="text-ink-gray-8">{{ `${prompt.doctype}.` }}</strong>
			</p>
			<ExtensionAccessChange v-if="prompt.access" :access="prompt.access" />

			<Checkbox v-if="isDestructive" v-model="understood" class="pt-3">
				<template #label>
					<span class="text-ink-red-6">
						{{ prompt.detail ? "Pages that use this field may break." : "This deletes the doctype." }}
					</span>
				</template>
			</Checkbox>

			<div class="flex justify-end gap-2 pt-4">
				<Button variant="subtle" @click="deny">Deny</Button>
				<Button variant="solid" :disabled="!canAllow" @click="allow">Allow</Button>
			</div>
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import ExtensionAccessChange from "@/extensions/components/ExtensionAccessChange.vue";
import { answerPrompt, pendingPrompt, type SchemaAct } from "@/extensions/data/confirmations";
import { Button, Checkbox } from "frappe-ui";
import { DialogTitle } from "reka-ui";
import { computed, ref, watch } from "vue";

const prompt = computed(() => pendingPrompt.value);
const understood = ref(false);

const actPhrases: Record<SchemaAct, string> = {
	create: "create the doctype",
	delete: "delete the doctype",
	"remove field": "remove the field",
	"change access": "change who can use",
};

// the user answers each question separately. If the tick stayed, one answer
// would approve an act that the user never saw
watch(prompt, () => (understood.value = false));

const isDestructive = computed(() => prompt.value?.act === "delete" || prompt.value?.act === "remove field");
const canAllow = computed(() => !isDestructive.value || understood.value);

const allow = () => answerPrompt(true);

/** The button, Escape and a click outside all count as no. */
const deny = () => answerPrompt(false);
</script>
