import { reactive, ref, watch } from "vue";
import type { UIElement } from "./cardAnswers";

export function isPreviewOnly(option: UIElement) {
	return !!(
		option.preview_only ||
		option.requires_acquisition ||
		option.license_status === "preview_only" ||
		option.asset_url === ""
	);
}

export function optionReply(option: UIElement): string {
	if (option.variant_id) return `${option.label || "This direction"}\n[design: ${option.variant_id}]`;
	const label = option.label || option.value || "";
	let reply = option.description ? `${label}: ${option.description}` : String(label);
	if (option.asset_id) reply += `\n[asset: ${option.asset_id}]`;
	if (isPreviewOnly(option)) reply += "\n[preview only; license/download and upload original]";
	else if (option.asset_url || option.image) reply += `\n[image: ${option.asset_url || option.image}]`;
	if (option.credit) reply += `\n[credit: ${option.credit}]`;
	if (option.source_url) reply += `\n[source: ${option.source_url}]`;
	if (option.license_url) reply += `\n[license: ${option.license_url}]`;
	return reply;
}

export function refinementReply(option: UIElement, changes: string): string {
	return `Tweak the "${option.label || "Design direction"}" preview (variant_id: ${option.variant_id}).\n${changes.trim()}\nRead its saved design specification and use it as the base. Show an updated preview for me to choose; keep the current page unchanged.`;
}

/** Message IDs keep a partially answered card independent of the selected chat. */
export function useCardDraft(messageId: () => string | undefined) {
	const stepIndex = ref(0);
	const selections = reactive<Record<number, Set<number>>>({});
	const inputs = reactive<Record<number, string>>({});
	const uploads = reactive<Record<number, string>>({});
	const colorSlots = reactive<Record<number, Record<number, string>>>({});
	const touchedColorSlots = reactive(new Set<string>());
	let restoring = false;
	const key = () => `bob:card:${messageId()}`;

	watch(
		messageId,
		() => {
			restoring = true;
			try {
				const saved = messageId() ? JSON.parse(localStorage.getItem(key()) || "null") : null;
				stepIndex.value = Math.max(0, Number(saved?.stepIndex) || 0);
				for (const record of [selections, inputs, uploads, colorSlots]) {
					Object.keys(record).forEach((index) => delete record[Number(index)]);
				}
				Object.entries(saved?.selections || {}).forEach(([index, values]) => {
					if (Array.isArray(values)) selections[Number(index)] = new Set(values);
				});
				Object.assign(inputs, saved?.inputs || {});
				Object.assign(uploads, saved?.uploads || {});
				Object.assign(colorSlots, saved?.colorSlots || {});
				touchedColorSlots.clear();
				for (const slot of saved?.touchedColorSlots || []) touchedColorSlots.add(slot);
			} catch {
				// Private browsing and storage quotas must not disable answering a card.
			} finally {
				restoring = false;
			}
		},
		{ immediate: true, flush: "sync" },
	);

	watch(
		[stepIndex, selections, inputs, uploads, colorSlots, touchedColorSlots],
		() => {
			if (restoring || !messageId()) return;
			try {
				localStorage.setItem(
					key(),
					JSON.stringify({
						stepIndex: stepIndex.value,
						selections: Object.fromEntries(
							Object.entries(selections).map(([index, values]) => [index, [...values]]),
						),
						inputs,
						uploads,
						colorSlots,
						touchedColorSlots: [...touchedColorSlots],
					}),
				);
			} catch {}
		},
		{ deep: true, flush: "sync" },
	);

	return { stepIndex, selections, inputs, uploads, colorSlots, touchedColorSlots };
}
