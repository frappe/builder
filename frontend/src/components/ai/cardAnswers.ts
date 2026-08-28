/** Pairing an agent UI card (`present_ui`) with the reply that answered it.
 * Shared, because the chat needs the same answer the card does: once a card
 * shows what was chosen, the reply bubble under it is a second copy of itself. */

export type UIElement = Record<string, any>;

/** Atoms the user acts on. `actions` is the submit row, not a question. */
export const INTERACTIVE_KINDS = new Set(["choices", "input", "upload", "actions", "color_input"]);

const LABELLABLE = new Set(["input", "choices", "upload"]);

export interface CardAnswer {
	question: string;
	answer: string;
}

/** A text atom right before an unlabelled control is that control's question —
 * the control renders it as its form label, so it must not render twice. */
export function isControlLabel(elements: UIElement[], i: number): boolean {
	const el = elements[i];
	const next = elements[i + 1];
	return (
		el?.kind === "text" && !!next && LABELLABLE.has(next.kind) && !next.label && !!String(el.text || "").trim()
	);
}

export function labelOfControl(elements: UIElement[], i: number): string {
	const el = elements[i];
	if (el?.label) return String(el.label);
	return isControlLabel(elements, i - 1) ? String(elements[i - 1].text || "") : "";
}

/** The question a choices/input atom answers: its own label, or the text atom
 * right above it (the model often writes the question as a separate line), or —
 * for the first question on the card — the lead-in the model wrote above it.
 * Every answer is keyed by this, so a question with no name anywhere can't be
 * paired with its answer and won't appear in the answered summary. */
export function labelOfQuestion(elements: UIElement[], i: number, lead?: string): string {
	const label = labelOfControl(elements, i);
	if (label) return label;
	const prev = elements[i - 1];
	if (prev?.kind === "text" || prev?.kind === "heading") return String(prev.text || "");
	const first = elements.findIndex((el) => INTERACTIVE_KINDS.has(el.kind) && el.kind !== "actions");
	return i === first ? String(lead || "") : "";
}

/** What was asked and what came back, once the card is answered. The reply was
 * built from the same labels the card renders, so pairing them up is a lookup —
 * there is no second copy of the answers to keep in sync, and it survives a
 * reload because the reply is just the next message in the chat. */
export function cardAnswers(elements: UIElement[], reply?: string, lead?: string): CardAnswer[] {
	const text = reply?.trim();
	if (!text) return [];
	const questions = elements
		.map((el, i) => ({ el, i }))
		.filter(({ el }) => INTERACTIVE_KINDS.has(el.kind) && el.kind !== "actions");
	const replied = new Map<string, string>();
	for (const line of text.split("\n")) {
		const at = line.indexOf(":");
		if (at > 0) replied.set(line.slice(0, at).trim(), line.slice(at + 1).trim());
	}
	const out = questions
		.map(({ i }) => ({
			question: labelOfQuestion(elements, i, lead),
			// "(suggested)" marks a preset the user left alone — it tells the model how
			// much latitude it has, and means nothing to the person reading it back.
			answer: (replied.get(labelOfQuestion(elements, i, lead)) || "").replace(/\s*\(suggested\)/g, ""),
		}))
		.filter((item) => item.question && item.answer);
	if (out.length) return out;
	// A lone tappable question submits the option itself ("Poster Wall: bold…"),
	// not a labelled line — the answer is what comes before the colon.
	if (questions.length === 1) {
		const first = text.split("\n")[0];
		const answer = (first.includes(":") ? first.slice(0, first.indexOf(":")) : first).trim();
		const question = labelOfQuestion(elements, questions[0].i, lead);
		if (question && answer) return [{ question, answer }];
	}
	return [];
}
