<template>
	<!-- Answered: the card collapses to what was asked and what was chosen. Replaying
	     a dead form of greyed-out controls tells the user nothing. -->
	<div
		v-if="answers.length"
		class="mt-2 w-full divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2 bg-surface-gray-1">
		<div v-for="(item, i) in answers" :key="i" class="px-3 py-2">
			<p class="text-p-xs leading-snug text-ink-gray-5">{{ item.question }}</p>
			<p class="mt-0.5 text-p-sm font-medium leading-snug text-ink-gray-8">{{ item.answer }}</p>
		</div>
	</div>

	<!-- A card that is ONLY tappable options renders flat: the option tiles are
	     cards already, and a second wrapper reads as a box-in-a-box. -->
	<div
		v-else
		class="mt-2 w-full space-y-2.5"
		:class="{ 'rounded-6 border border-outline-gray-2 bg-surface-gray-1 p-3': hasChrome }">
		<!-- Several questions in one card walk one at a time: the whole set is asked
		     in a single turn, and the user still meets them one decision at a time. -->
		<div v-if="isStepped" class="flex items-center justify-between">
			<span class="text-p-xs font-medium text-ink-gray-5">{{ stepIndex + 1 }} of {{ steps.length }}</span>
			<div class="flex items-center gap-1">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-left"
					:disabled="stepIndex === 0 || !interactive || disabled"
					@click="goBack" />
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-right"
					:disabled="isLastStep || !interactive || disabled"
					@click="goNext" />
			</div>
		</div>

		<template v-for="{ el, i } in visibleElements" :key="i">
			<!-- heading -->
			<p v-if="el.kind === 'heading'" class="text-p-sm font-semibold leading-snug text-ink-gray-8">
				{{ el.text }}
			</p>

			<!-- text: a line right before an unlabelled control IS that control's label —
			     it renders inside the control (form-label size, hugging it), not here -->
			<p
				v-else-if="el.kind === 'text' && !consumedAsLabel(i)"
				class="whitespace-pre-line text-p-sm leading-snug text-ink-gray-7">
				{{ el.text }}
			</p>

			<!-- list -->
			<ul v-else-if="el.kind === 'list'" class="m-0 list-none space-y-1 p-0">
				<li
					v-for="(item, j) in el.items || []"
					:key="j"
					class="flex items-start gap-2 text-p-sm leading-snug text-ink-gray-7">
					<span class="mt-[6px] size-1 shrink-0 rounded-full bg-surface-gray-4" />
					<span class="min-w-0 break-words">{{ item }}</span>
				</li>
			</ul>

			<!-- swatches -->
			<div v-else-if="el.kind === 'swatches'" class="flex flex-wrap items-center gap-1.5">
				<span class="flex overflow-hidden rounded-4 border border-black/10">
					<span
						v-for="color in (el.colors || []).slice(0, 8)"
						:key="color"
						class="size-3.5"
						:style="{ backgroundColor: color }"
						:title="color" />
				</span>
				<span v-if="el.label" class="text-xs text-ink-gray-5">{{ el.label }}</span>
			</div>

			<!-- image -->
			<figure v-else-if="el.kind === 'image' && safeSrc(el.src)" class="m-0">
				<img :src="el.src" class="max-h-48 w-auto max-w-full rounded-4 border border-outline-gray-2" alt="" />
				<figcaption v-if="el.caption" class="mt-1 text-xs text-ink-gray-5">{{ el.caption }}</figcaption>
			</figure>

			<!-- divider -->
			<hr v-else-if="el.kind === 'divider'" class="border-outline-gray-1" />

			<!-- choices -->
			<div v-else-if="el.kind === 'choices'" class="w-full" :class="{ '!mt-4': i > 0 && controlLabel(i) }">
				<p v-if="controlLabel(i)" class="mb-1.5 text-xs font-medium text-ink-gray-6">
					{{ controlLabel(i) }}
				</p>
				<div class="flex w-full flex-wrap gap-2">
					<div v-for="(option, j) in el.options || []" :key="j" class="flex flex-1 basis-48 flex-col gap-1.5">
						<button
							:disabled="!interactive || disabled"
							class="group flex w-full flex-1 flex-col items-start gap-2 rounded-6 border px-3 py-2.5 text-left transition-all disabled:cursor-not-allowed disabled:opacity-50"
							:class="
								isSelected(i, j)
									? 'border-outline-gray-4 bg-surface-gray-2'
									: 'bg-surface-white border-outline-gray-2 hover:border-outline-gray-3 hover:bg-surface-gray-2'
							"
							@click="onOptionClick(i, el, j, option)">
							<!-- photo option (search_images thumb): the picture IS the choice -->
							<img
								v-if="option.image && safeSrc(option.image)"
								:src="option.image"
								class="w-full rounded-4 border border-black/10"
								:class="option.variant_id ? 'max-h-64 object-contain' : 'h-24 object-cover'"
								loading="lazy"
								alt="" />
							<img
								v-if="option.mobile_image && safeSrc(option.mobile_image)"
								:src="option.mobile_image"
								class="max-h-32 w-auto rounded border border-black/10"
								loading="lazy"
								alt="Mobile layout preview" />
							<span
								v-else-if="option.colors?.length"
								class="flex shrink-0 overflow-hidden rounded-4 border border-black/10">
								<span
									v-for="color in option.colors.slice(0, 5)"
									:key="color"
									class="size-3.5"
									:style="{ backgroundColor: color }" />
							</span>
							<span v-if="isPreviewOnly(option)" class="text-p-xs font-medium text-ink-amber-8">
								Preview only
							</span>
							<span class="text-p-sm font-medium leading-snug text-ink-gray-8">{{ option.label }}</span>
							<span v-if="option.description" class="line-clamp-3 text-p-xs leading-snug text-ink-gray-5">
								{{ option.description }}
							</span>
						</button>
						<a
							v-if="isPreviewOnly(option) && safeSrc(option.source_url)"
							:href="option.source_url"
							target="_blank"
							rel="noopener noreferrer"
							class="px-1 text-p-xs text-ink-gray-6 underline">
							Open original library page
						</a>
					</div>
				</div>
			</div>

			<!-- input -->
			<FormControl
				v-else-if="el.kind === 'input'"
				v-model="inputs[i]"
				type="text"
				:class="{ '!mt-4': i > 0 && controlLabel(i) }"
				:label="controlLabel(i)"
				:placeholder="el.placeholder || ''"
				:disabled="!interactive || disabled"
				autocomplete="off"
				@keydown.enter.prevent="onInputEnter()" />

			<!-- upload: the user's own image (logo, photo); URL rides the reply -->
			<div v-else-if="el.kind === 'upload'" class="w-full">
				<span v-if="controlLabel(i)" class="mb-1 block text-p-xs text-ink-gray-5">
					{{ controlLabel(i) }}
				</span>
				<FileUploader
					fileTypes="image/*"
					:private="false"
					folder="Home/Builder Uploads"
					uploadEndpoint="/api/method/builder.api.upload_builder_asset"
					@success="(file: any) => (uploads[i] = file.file_url)">
					<template #default="{ openFileSelector, uploading, progress }">
						<div class="flex items-center gap-2">
							<img
								v-if="uploads[i]"
								:src="uploads[i]"
								class="h-10 w-14 rounded-4 border border-outline-gray-2 object-cover"
								alt="" />
							<Button
								size="sm"
								variant="subtle"
								:disabled="!interactive || disabled || uploading"
								@click="openFileSelector()">
								{{ uploading ? `Uploading ${progress}%` : uploads[i] ? "Replace image" : "Upload image" }}
							</Button>
						</div>
					</template>
				</FileUploader>
			</div>

			<!-- color_input: LABELLED role slots (Brand/Background/Accent/Text…) the model
			     defines, each a Builder ColorInput — so the reply says which colour goes
			     WHERE, not a random pile of swatches. Every slot is optional. -->
			<div v-else-if="el.kind === 'color_input'" class="w-full">
				<span v-if="controlLabel(i)" class="mb-1.5 block text-p-xs font-medium text-ink-gray-5">
					{{ controlLabel(i) }}
				</span>
				<div class="flex flex-col gap-2.5">
					<div v-for="(slot, k) in colorSlotDefs(el)" :key="k" class="flex flex-col gap-1">
						<span class="text-p-sm text-ink-gray-7">{{ slot.label }}</span>
						<span v-if="slot.hint" class="-mt-0.5 text-p-xs text-ink-gray-4">{{ slot.hint }}</span>
						<ColorInput
							:modelValue="colorSlots[i]?.[k] || null"
							:showColorVariableOptions="false"
							placement="left"
							placeholder="Pick a colour"
							@update:modelValue="(c: string) => setColorSlot(i, k, c)" />
					</div>
				</div>
			</div>

			<!-- actions -->
			<div v-else-if="el.kind === 'actions'" class="flex flex-wrap gap-2 pt-0.5">
				<Button
					v-for="(btn, j) in el.buttons || []"
					:key="j"
					size="xs"
					:variant="btn.variant === 'secondary' ? 'subtle' : 'solid'"
					:disabled="!interactive || disabled"
					@click="submitCollected(btn.label)">
					{{ btn.label }}
				</Button>
			</div>
		</template>
		<!-- Stepping forward is the only control a mid-card step needs; the model's
		     own actions row belongs to the last step and renders in the loop above. -->
		<Button
			v-if="isStepped && !isLastStep"
			variant="subtle"
			:disabled="!interactive || disabled"
			@click="goNext">
			Next
		</Button>
		<!-- A waiting card with nothing tappable strands the user (e.g. a form the
		     model forgot to put buttons on) — give it a default way forward. -->
		<div v-if="interactive && needsSubmit && (!isStepped || isLastStep)" class="flex gap-2 pt-0.5">
			<Button size="xs" variant="solid" :disabled="disabled" @click="submitCollected('Looks good, go ahead')">
				Looks good, go ahead
			</Button>
		</div>
		<p v-if="interactive && hasChoices && !isStepped" class="text-xs text-ink-gray-4">
			Or describe something different below
		</p>
	</div>
</template>

<script setup lang="ts">
import ColorInput from "@/components/Controls/ColorInput.vue";
import { Button, FileUploader, FormControl } from "frappe-ui";
import { computed, watchEffect } from "vue";
import { isPreviewOnly, optionReply, useCardDraft } from "./cardDraft";
import {
	INTERACTIVE_KINDS,
	typedCardAnswers,
	type CardSubmission,
	isControlLabel,
	labelOfControl,
	labelOfQuestion,
	type UIElement,
} from "./cardAnswers";

/** Generic renderer for the agent's `present_ui` cards. The agent composes a
 * card from atoms (heading/text/list/swatches/image/choices/input/actions);
 * this component renders them and turns the user's interaction into one plain
 * chat reply. Unknown element kinds are skipped, so the agent can be ahead of
 * the renderer without breaking. */

const props = defineProps<{
	ui: UIElement[];
	messageId?: string;
	interactive: boolean;
	disabled?: boolean;
	/** The reply this card was answered with, once it has been. submitCollected
	 * writes "Question: answer" lines, so the card can show what was chosen
	 * without the answers needing to be stored a second time. */
	answeredWith?: string;
	answer?: CardSubmission;
	/** The card's lead-in — the question the model wrote above the controls. It
	 * names the first question when that atom carries no label of its own. */
	lead?: string;
}>();

/** `reply` is the full text the model receives; `display` is the compact line
 * the chat shows as the user's message (option label, typed values). */
const emit = defineEmits<{ submit: [reply: string, display?: string, answer?: CardSubmission] }>();

const elements = computed(() => (Array.isArray(props.ui) ? props.ui : []));
const hasChoices = computed(() => elements.value.some((el) => el.kind === "choices"));
// Option tiles are cards already, so ANY card containing choices renders flat —
// its other atoms (heading, upload, actions) sit between the tiles unboxed.
// Only choice-less cards (pure forms, plans) get the wrapper box.
const hasChrome = computed(() => !hasChoices.value);

// --- steps -------------------------------------------------------------------
// The agent asks everything it needs in ONE card (one turn instead of four), and
// the card walks the user through it a question at a time.

// What starts a new step. `upload` never does: it arrives as the "or your own"
// escape hatch beneath a choices group and belongs to that same question.
const QUESTION_KINDS = new Set(["choices", "input", "color_input"]);

/** Element indices grouped into steps. Each step is one question plus whatever
 * introduces or decorates it; anything trailing the last question (the actions
 * row) joins the final step, so the card always ends on its submit button. */
const steps = computed<number[][]>(() => {
	const out: number[][] = [];
	let pending: number[] = [];
	elements.value.forEach((el, i) => {
		pending.push(i);
		// An unlabelled input straight after a question is that question's escape
		// hatch ("or paste a link"), not a question of its own.
		const escapeHatch = el.kind === "input" && !el.label && !consumedAsLabel(i - 1);
		if (out.length && (escapeHatch || el.kind === "upload")) {
			out[out.length - 1].push(...pending);
			pending = [];
			return;
		}
		if (QUESTION_KINDS.has(el.kind) && !(escapeHatch && out.length)) {
			out.push(pending);
			pending = [];
		}
	});
	if (pending.length) {
		if (out.length) out[out.length - 1].push(...pending);
		else out.push(pending);
	}
	return out;
});

const { stepIndex, selections, inputs, uploads, colorSlots, touchedColorSlots } = useCardDraft(
	() => props.messageId,
);
const isStepped = computed(() => steps.value.length > 1 && props.interactive && !props.answeredWith);
const isLastStep = computed(() => stepIndex.value >= steps.value.length - 1);

/** The atoms on screen right now — every atom when the card isn't stepped. */
const visibleElements = computed(() => {
	const indices = isStepped.value
		? steps.value[Math.min(stepIndex.value, steps.value.length - 1)] || []
		: elements.value.map((_, i) => i);
	return indices.map((i) => ({ el: elements.value[i], i }));
});

function goNext() {
	if (isLastStep.value) return;
	stepIndex.value += 1;
}

// Enter on a mid-card input answers THAT step, not the whole card.
function onInputEnter() {
	if (isStepped.value && !isLastStep.value) goNext();
	else submitCollected();
}

function goBack() {
	if (stepIndex.value > 0) stepIndex.value -= 1;
}

const answers = computed(() => typedCardAnswers(elements.value, props.answer));
// A choices group with zero options renders nothing tappable — it must not
// count as interactive, or it suppresses the fallback button and dead-ends the card.
const interactiveAtoms = computed(() =>
	elements.value.filter(
		(el) =>
			INTERACTIVE_KINDS.has(el.kind) &&
			(el.kind !== "choices" || el.options?.length) &&
			(el.kind !== "actions" || el.buttons?.some((button: UIElement) => button.label)),
	),
);
// A card that is ONE question (a single choices group, nothing else to fill in):
// tapping an option IS the answer. In a bigger form a tap is just a pick — the
// action button submits everything together.
const isSingleQuestion = computed(
	() => interactiveAtoms.value.length === 1 && interactiveAtoms.value[0].kind === "choices",
);
const needsSubmit = computed(
	() =>
		!interactiveAtoms.value.some((element) => element.kind === "actions") &&
		!(isSingleQuestion.value && !interactiveAtoms.value[0].multi),
);

const consumedAsLabel = (i: number) => isControlLabel(elements.value, i);
const controlLabel = (i: number) => labelOfControl(elements.value, i);
const atomLabel = (i: number) => labelOfQuestion(elements.value, i, props.lead);

/** Only plain CSS color literals reach inline styles — a url(...) or var() from
 * the model must not become a style injection vector. */
function safeColor(value: unknown): string | undefined {
	const color = String(value ?? "").trim();
	return /^(#[0-9a-fA-F]{3,8}|rgba?\([\d\s.,%]+\)|hsla?\([\d\s.,%deg]+\)|[a-zA-Z]{3,20})$/.test(color)
		? color
		: undefined;
}

/** The role slots a color_input offers. The model sends `colors: [{label, hint?,
 * value?}]` — `value` is a curated preset hex shown as the starting point — with
 * a fallback to one slot named after the atom's own label. */
function colorSlotDefs(el: UIElement): { label: string; hint?: string; value?: string }[] {
	const defs = Array.isArray(el.colors) ? el.colors : [];
	const clean = defs
		.filter((d: any) => d && typeof d === "object" && d.label)
		.map((d: any) => ({
			label: String(d.label),
			hint: d.hint ? String(d.hint) : undefined,
			value: safeColor(d.value),
		}));
	return clean.length ? clean : [{ label: el.label || "Colour" }];
}

// Seed preset values into the collected state so an untouched slot still submits
// its preset. Never re-seed a slot the user touched (clearing one means "you pick").
watchEffect(() => {
	elements.value.forEach((el, i) => {
		if (el.kind !== "color_input") return;
		colorSlotDefs(el).forEach((slot, k) => {
			if (slot.value && !touchedColorSlots.has(`${i}:${k}`) && !colorSlots[i]?.[k]) {
				colorSlots[i] ??= {};
				colorSlots[i][k] = slot.value;
			}
		});
	});
});

function setColorSlot(i: number, k: number, color: string) {
	touchedColorSlots.add(`${i}:${k}`);
	colorSlots[i] ??= {};
	if (color) colorSlots[i][k] = color;
	else delete colorSlots[i][k];
}

function isSelected(elIndex: number, optIndex: number): boolean {
	return selections[elIndex]?.has(optIndex) ?? false;
}

function onOptionClick(elIndex: number, el: UIElement, optIndex: number, option: UIElement) {
	if (!el.multi && isSingleQuestion.value) {
		selections[elIndex] = new Set([optIndex]);
		emit("submit", optionReply(option), String(option.label || option.value || ""), collectAnswers());
		return;
	}
	selections[elIndex] ??= new Set();
	if (!el.multi) {
		// Radio pick inside a form: record it, the action button submits the lot.
		// Submitting on tap here silently threw away every other answer on the card.
		selections[elIndex].clear();
		selections[elIndex].add(optIndex);
		// Picking IS the answer to a stepped question, so move straight on rather
		// than making the user confirm a choice they can still step back and change.
		if (isStepped.value && !isLastStep.value) goNext();
		return;
	}
	selections[elIndex].has(optIndex)
		? selections[elIndex].delete(optIndex)
		: selections[elIndex].add(optIndex);
}

/** Compose one plain-text reply from the clicked action + everything collected.
 * Reads like a normal user message, so the model needs no special parsing. The
 * labelled long form goes to the model; the chat shows just the values. */
function submitCollected(actionLabel?: string) {
	const lines: string[] = actionLabel ? [actionLabel] : [];
	const values: string[] = [];
	elements.value.forEach((el, i) => {
		if (el.kind === "choices" && selections[i]?.size) {
			const picked = [...selections[i]].map((j) => el.options?.[j]).filter(Boolean);
			if (picked.length) {
				lines.push(`${atomLabel(i) || "Selected"}: ${picked.map(optionReply).join("\n")}`);
				values.push(picked.map((option) => option.label || option.value || "").join(", "));
			}
		}
		if (el.kind === "input" && inputs[i]?.trim()) {
			const label = atomLabel(i);
			lines.push(label ? `${label}: ${inputs[i].trim()}` : inputs[i].trim());
			values.push(inputs[i].trim());
		}
		if (el.kind === "upload" && uploads[i]) {
			lines.push(`${el.label || "Uploaded image"}: ${uploads[i]}`);
			values.push(`${el.label || "image"} uploaded`);
		}
		if (el.kind === "color_input") {
			const picked = colorSlotDefs(el)
				.map((slot, k) => ({
					label: slot.label,
					hex: colorSlots[i]?.[k],
					// A preset the user never touched is a suggestion, not a decision —
					// the model may refine it; a touched slot is the user's law.
					suggested: !touchedColorSlots.has(`${i}:${k}`) && colorSlots[i]?.[k] === slot.value,
				}))
				.filter((s) => s.hex);
			if (picked.length) {
				// Explicit role→hex mapping so the model uses each colour WHERE the user
				// meant it (never a random spread): "Brand: #C4552D, Background: #F4EFE8".
				// Untouched presets carry "(suggested)" so the model keeps creative
				// latitude on them while treating user-picked slots as law.
				// "<question>: Brand: #C4552D, Background: #F4EFE8" — the leading label
				// keys it to its question (everything after the FIRST colon is the
				// answer), and the role→hex pairs read the same to the model as ever.
				lines.push(
					`${atomLabel(i) || "Colours"}: ${picked
						.map((s) => `${s.label}: ${s.hex}${s.suggested ? " (suggested)" : ""}`)
						.join(", ")}`,
				);
				values.push(picked.map((s) => s.hex).join(" "));
			}
		}
	});
	const reply = lines.join("\n").trim();
	if (reply) emit("submit", reply, values.join(" · ") || actionLabel, collectAnswers());
}

function collectAnswers(): CardSubmission {
	const answers: CardSubmission["answers"] = [];
	elements.value.forEach((field, i) => {
		const fieldId = field.id || `field-${i}`;
		if (field.kind === "choices" && selections[i]?.size) {
			const indices = [...selections[i]];
			answers.push({
				fieldId,
				value: indices.map((j) => field.options[j].label || field.options[j].value),
				optionIds: indices.map((j) => field.options[j].id || `option-${j}`),
			});
		} else if (field.kind === "input" && inputs[i]?.trim()) {
			answers.push({ fieldId, value: inputs[i].trim() });
		} else if (field.kind === "upload" && uploads[i]) {
			answers.push({ fieldId, value: uploads[i] });
		} else if (field.kind === "color_input" && colorSlots[i]) {
			answers.push({ fieldId, value: colorSlots[i] });
		}
	});
	return { cardId: props.messageId || "", answers };
}

/** Same-origin paths and https only — the spec comes from the model. */
function safeSrc(src: unknown): boolean {
	if (typeof src !== "string" || !src) return false;
	return (src.startsWith("/") && !src.startsWith("//")) || src.startsWith("https://");
}
</script>
