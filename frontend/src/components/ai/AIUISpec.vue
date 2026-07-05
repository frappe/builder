<template>
	<!-- A card that is ONLY tappable options renders flat: the option tiles are
	     cards already, and a second wrapper reads as a box-in-a-box. -->
	<div
		class="mt-2 w-full space-y-2.5"
		:class="{ 'rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3': hasChrome }">
		<template v-for="(el, i) in elements" :key="i">
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
				<span class="flex overflow-hidden rounded border border-black/10">
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
				<img :src="el.src" class="max-h-48 w-auto max-w-full rounded border border-outline-gray-2" alt="" />
				<figcaption v-if="el.caption" class="mt-1 text-xs text-ink-gray-5">{{ el.caption }}</figcaption>
			</figure>

			<!-- inline svg figure. Fixed height, not max-height: tall figures (plan
			     wireframes) scale down to fit instead of being cropped mid-page. -->
			<figure v-else-if="el.kind === 'svg' && el.svg" class="m-0">
				<div
					class="ai-sketch h-64 w-full overflow-hidden rounded border border-outline-gray-2"
					v-html="sanitizeSvg(el.svg)" />
				<figcaption v-if="el.caption" class="mt-1 text-xs text-ink-gray-5">{{ el.caption }}</figcaption>
			</figure>

			<!-- mock: a deterministic mini-page rendered from plan data (sections,
			     palette, fonts) — replaces the model-drawn SVG strip AND the section
			     list on plan cards. Real fonts, real colors, readable section names. -->
			<div
				v-else-if="el.kind === 'mock' && el.sections?.length"
				class="w-full overflow-hidden rounded-md border border-outline-gray-2">
				<div
					v-for="(section, j) in el.sections.slice(0, 8)"
					:key="j"
					class="px-3"
					:class="j === 0 ? 'py-5' : 'py-2.5'"
					:style="{ backgroundColor: safeColor(section.bg), color: safeColor(section.ink) }">
					<p
						class="m-0 truncate leading-tight"
						:class="j === 0 ? 'text-base font-bold' : 'text-xs font-semibold'"
						:style="{ fontFamily: el.fonts?.heading }">
						{{ section.headline || section.name }}
					</p>
					<p
						v-if="section.detail"
						class="m-0 mt-0.5 truncate text-[11px] leading-snug opacity-75"
						:style="{ fontFamily: el.fonts?.body }">
						{{ section.detail }}
					</p>
				</div>
			</div>

			<!-- divider -->
			<hr v-else-if="el.kind === 'divider'" class="border-outline-gray-1" />

			<!-- choices -->
			<div
				v-else-if="el.kind === 'choices'"
				class="w-full"
				:class="{ '!mt-4': i > 0 && controlLabel(i, el) }">
				<p v-if="controlLabel(i, el)" class="mb-1.5 text-xs font-medium text-ink-gray-6">
					{{ controlLabel(i, el) }}
				</p>
				<div class="flex w-full flex-wrap gap-2">
					<button
						v-for="(option, j) in el.options || []"
						:key="j"
						:disabled="!interactive || disabled"
						class="group flex flex-1 basis-48 flex-col items-start gap-2 rounded-lg border px-3 py-2.5 text-left transition-all disabled:cursor-not-allowed disabled:opacity-50"
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
							class="h-24 w-full rounded border border-black/10 object-cover"
							loading="lazy"
							alt="" />
						<!-- minimal layout sketch: the model draws an abstract wireframe SVG.
						     The sketch already carries the option's palette, so no swatch strip. -->
						<span
							v-else-if="option.svg"
							class="ai-sketch h-20 w-full overflow-hidden rounded border border-black/10"
							v-html="sanitizeSvg(option.svg)" />
						<span
							v-else-if="option.colors?.length && !option.font"
							class="flex shrink-0 overflow-hidden rounded border border-black/10">
							<span
								v-for="color in option.colors.slice(0, 5)"
								:key="color"
								class="size-3.5"
								:style="{ backgroundColor: color }" />
						</span>
						<!-- Full type specimen (loaded on render via fontManager). On a pure
						     typography option the fonts speak for themselves; when the model
						     mixes a specimen onto a visual option, the label must survive. -->
						<template v-if="option.font?.heading">
							<span
								v-if="option.label && (option.svg || option.image)"
								class="text-p-sm font-medium leading-snug text-ink-gray-8">
								{{ option.label }}
							</span>
							<span
								class="text-2xl leading-tight text-ink-gray-9"
								:style="{ fontFamily: option.font.heading, fontWeight: 700 }">
								{{ option.font.heading }}
							</span>
							<span
								v-if="option.font.body"
								class="text-p-sm leading-snug text-ink-gray-7"
								:style="{ fontFamily: option.font.body }">
								{{ option.font.body }} · The quick brown fox jumps over the lazy dog. 0123456789
							</span>
						</template>
						<template v-else>
							<span class="text-p-sm font-medium leading-snug text-ink-gray-8">{{ option.label }}</span>
							<!-- A sketch option is chosen on looks — the description only reaches
							     the model (spec + tap reply), not the eye. -->
							<span
								v-if="option.description && !option.svg"
								class="line-clamp-3 text-xs leading-snug text-ink-gray-5">
								{{ option.description }}
							</span>
						</template>
					</button>
				</div>
			</div>

			<!-- input -->
			<FormControl
				v-else-if="el.kind === 'input'"
				v-model="inputs[i]"
				type="text"
				:class="{ '!mt-4': i > 0 && controlLabel(i, el) }"
				:label="controlLabel(i, el)"
				:placeholder="el.placeholder || ''"
				:disabled="!interactive || disabled"
				autocomplete="off"
				@keydown.enter.prevent="submitCollected()" />

			<!-- upload: the user's own image (logo, photo); URL rides the reply -->
			<div v-else-if="el.kind === 'upload'" class="w-full">
				<span v-if="controlLabel(i, el)" class="mb-1 block text-p-xs text-ink-gray-5">
					{{ controlLabel(i, el) }}
				</span>
				<FileUploader
					fileTypes="image/*"
					:uploadArgs="{
						private: false,
						folder: 'Home/Builder Uploads',
						upload_endpoint: '/api/method/builder.api.upload_builder_asset',
					}"
					@success="(file: any) => (uploads[i] = file.file_url)">
					<template #default="{ openFileSelector, uploading, progress }">
						<div class="flex items-center gap-2">
							<img
								v-if="uploads[i]"
								:src="uploads[i]"
								class="h-10 w-14 rounded border border-outline-gray-2 object-cover"
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
		<!-- A waiting card with nothing tappable strands the user (e.g. a plan the
		     model forgot to put buttons on) — give it a default way forward. -->
		<div v-if="interactive && !hasInteractiveAtoms" class="flex gap-2 pt-0.5">
			<Button size="xs" variant="solid" :disabled="disabled" @click="submitCollected('Looks good, go ahead')">
				Looks good, go ahead
			</Button>
		</div>
		<p v-if="interactive && hasChoices" class="text-xs text-ink-gray-4">
			Or describe something different below
		</p>
	</div>
</template>

<script setup lang="ts">
import { setFont } from "@/utils/fontManager";
import DOMPurify from "dompurify";
import { Button, FileUploader, FormControl } from "frappe-ui";
import { computed, reactive, watchEffect } from "vue";

/** Generic renderer for the agent's `present_ui` cards. The agent composes a
 * card from atoms (heading/text/list/swatches/image/choices/input/actions);
 * this component renders them and turns the user's interaction into one plain
 * chat reply. Unknown element kinds are skipped, so the agent can be ahead of
 * the renderer without breaking. */

type UIElement = Record<string, any>;

const props = defineProps<{
	ui: UIElement[];
	interactive: boolean;
	disabled?: boolean;
}>();

/** `reply` is the full text the model receives; `display` is the compact line
 * the chat shows as the user's message (option label, typed values). */
const emit = defineEmits<{ submit: [reply: string, display?: string] }>();

const elements = computed(() => (Array.isArray(props.ui) ? props.ui : []));
const hasChoices = computed(() => elements.value.some((el) => el.kind === "choices"));
// Option tiles are cards already, so ANY card containing choices renders flat —
// its other atoms (heading, upload, actions) sit between the tiles unboxed.
// Only choice-less cards (pure forms, plans) get the wrapper box.
const hasChrome = computed(() => !hasChoices.value);

const INTERACTIVE_KINDS = new Set(["choices", "input", "upload", "actions"]);
const interactiveAtoms = computed(() => elements.value.filter((el) => INTERACTIVE_KINDS.has(el.kind)));
const hasInteractiveAtoms = computed(() => interactiveAtoms.value.length > 0);
// A card that is ONE question (a single choices group, nothing else to fill in):
// tapping an option IS the answer. In a bigger form a tap is just a pick — the
// action button submits everything together.
const isSingleQuestion = computed(
	() => interactiveAtoms.value.length === 1 && interactiveAtoms.value[0].kind === "choices",
);

const LABELLABLE = new Set(["input", "choices", "upload"]);

/** A text atom right before an unlabelled control is that control's question —
 * the control renders it as its form label, so it must not render twice. */
function consumedAsLabel(i: number): boolean {
	const el = elements.value[i];
	const next = elements.value[i + 1];
	return (
		el?.kind === "text" &&
		!!next &&
		LABELLABLE.has(next.kind) &&
		!next.label &&
		!!String(el.text || "").trim()
	);
}

function controlLabel(i: number, el: UIElement): string {
	if (el.label) return String(el.label);
	return consumedAsLabel(i - 1) ? String(elements.value[i - 1].text || "") : "";
}

// Load the Google Fonts referenced by option specimens and plan mocks (cached
// in fontManager, so re-renders are free). Heading fonts also need their bold face.
watchEffect(() => {
	for (const el of elements.value) {
		if (el.kind === "mock") {
			if (el.fonts?.heading) setFont(el.fonts.heading, "700");
			if (el.fonts?.body) setFont(el.fonts.body);
			continue;
		}
		if (el.kind !== "choices") continue;
		for (const option of el.options || []) {
			if (option?.font?.heading) setFont(option.font.heading, "700");
			if (option?.font?.body) setFont(option.font.body);
		}
	}
});

/** Only plain CSS color literals reach inline styles — a url(...) or var() from
 * the model must not become a style injection vector. */
function safeColor(value: unknown): string | undefined {
	const color = String(value ?? "").trim();
	return /^(#[0-9a-fA-F]{3,8}|rgba?\([\d\s.,%]+\)|hsla?\([\d\s.,%deg]+\)|[a-zA-Z]{3,20})$/.test(color)
		? color
		: undefined;
}

// Collected state keyed by element index: multi-select picks, typed inputs,
// uploaded file URLs.
const selections = reactive<Record<number, Set<number>>>({});
const inputs = reactive<Record<number, string>>({});
const uploads = reactive<Record<number, string>>({});

function isSelected(elIndex: number, optIndex: number): boolean {
	return selections[elIndex]?.has(optIndex) ?? false;
}

function optionReply(option: UIElement): string {
	const label = option.label || option.value || "";
	let reply = option.description ? `${label}: ${option.description}` : String(label);
	// The model needs the exact URL of a picked photo to place it in the page.
	if (option.image) reply += `\n(chosen image: ${option.image})`;
	return reply;
}

function onOptionClick(elIndex: number, el: UIElement, optIndex: number, option: UIElement) {
	if (!el.multi && isSingleQuestion.value) {
		emit("submit", optionReply(option), String(option.label || option.value || ""));
		return;
	}
	selections[elIndex] ??= new Set();
	if (!el.multi) {
		// Radio pick inside a form: record it, the action button submits the lot.
		// Submitting on tap here silently threw away every other answer on the card.
		selections[elIndex].clear();
		selections[elIndex].add(optIndex);
		return;
	}
	selections[elIndex].has(optIndex)
		? selections[elIndex].delete(optIndex)
		: selections[elIndex].add(optIndex);
}

/** The question a choices/input atom answers: its own label, or the text atom
 * right above it (the model often writes the question as a separate line). */
function atomLabel(i: number, el: UIElement): string {
	const label = controlLabel(i, el);
	if (label) return label;
	const prev = elements.value[i - 1];
	return prev?.kind === "text" || prev?.kind === "heading" ? String(prev.text || "") : "";
}

/** Compose one plain-text reply from the clicked action + everything collected.
 * Reads like a normal user message, so the model needs no special parsing. The
 * labelled long form goes to the model; the chat shows just the values. */
function submitCollected(actionLabel?: string) {
	const lines: string[] = actionLabel ? [actionLabel] : [];
	const values: string[] = [];
	elements.value.forEach((el, i) => {
		if (el.kind === "choices" && selections[i]?.size) {
			const picked = [...selections[i]]
				.map((j) => (el.options?.[j] ? el.options[j].label : ""))
				.filter(Boolean);
			if (picked.length) {
				lines.push(`${atomLabel(i, el) || "Selected"}: ${picked.join(", ")}`);
				values.push(picked.join(", "));
			}
		}
		if (el.kind === "input" && inputs[i]?.trim()) {
			const label = atomLabel(i, el);
			lines.push(label ? `${label}: ${inputs[i].trim()}` : inputs[i].trim());
			values.push(inputs[i].trim());
		}
		if (el.kind === "upload" && uploads[i]) {
			lines.push(`${el.label || "Uploaded image"}: ${uploads[i]}`);
			values.push(`${el.label || "image"} uploaded`);
		}
	});
	const reply = lines.join("\n").trim();
	if (reply) emit("submit", reply, values.join(" · ") || actionLabel);
}

/** Same-origin paths and https only — the spec comes from the model. */
function safeSrc(src: unknown): boolean {
	if (typeof src !== "string" || !src) return false;
	return src.startsWith("/") || src.startsWith("https://");
}

/** Model-drawn sketches are untrusted markup: strip everything but plain SVG. */
function sanitizeSvg(svg: unknown): string {
	if (typeof svg !== "string") return "";
	return DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true } });
}
</script>

<style scoped>
/* Sketch SVGs arrive with a viewBox but arbitrary width/height — scale to the box. */
.ai-sketch :deep(svg) {
	display: block;
	width: 100%;
	height: 100%;
}
</style>
