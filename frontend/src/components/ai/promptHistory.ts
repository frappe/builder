import type { Ref } from "vue";

/** The caret is on the first line (going up) or the last line (going down). */
export function caretAtEdge(el: HTMLTextAreaElement, up: boolean): boolean {
	const { value, selectionStart, selectionEnd } = el;
	return up ? !value.slice(0, selectionStart).includes("\n") : !value.slice(selectionEnd).includes("\n");
}

/** Up and Down through the prompts sent earlier, shell-style. It starts only from an
 * empty composer and keeps going while the composer still shows a recalled prompt, so
 * the keys go on moving the caret in a draft. `sent` is newest first. */
export function usePromptHistory(prompt: Ref<string>, sent: () => string[]) {
	let index = -1;

	/** Returns true when it took the key. */
	function step(older: boolean, el: HTMLTextAreaElement): boolean {
		const prompts = sent();
		const browsing = index >= 0 && prompt.value === prompts[index];
		if (!browsing) index = -1;
		const takes = browsing ? caretAtEdge(el, older) : older && !prompt.value;
		if (!takes) return false;
		index = Math.min(index + (older ? 1 : -1), prompts.length - 1);
		prompt.value = index < 0 ? "" : prompts[index];
		return true;
	}

	return { step };
}
