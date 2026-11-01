import type { AIRunEvent } from "./types";

/** A high-water mark would drop after-commit tool batches delivered after live text. */
export class RunEvents {
	private runs = new Map<string, { seen: Set<number>; finished: boolean }>();

	accept(event: AIRunEvent) {
		if (!event.run_id || !Number.isInteger(event.seq)) return false;
		let run = this.runs.get(event.run_id);
		if (!run) {
			run = { seen: new Set(), finished: false };
			this.runs.set(event.run_id, run);
		}
		if (run.finished || run.seen.has(event.seq)) return false;
		run.seen.add(event.seq);
		return true;
	}

	finished(runId: string) {
		return this.runs.get(runId)?.finished ?? false;
	}

	finish(runId: string) {
		if (runId) this.runs.set(runId, { seen: new Set(), finished: true });
	}

	clear() {
		this.runs.clear();
	}
}

export interface SendEnvelope {
	requestId: string;
	pageId: string;
	sessionId: string;
	model: string;
	prompt: string;
	blocks: { id: string; label: string }[];
	imageData: string | null;
	imagePreviewUrl: string | null;
	imageFileName: string;
	displayText: string | null;
	canvasTheme: string;
	attempted: boolean;
}

/** Tab-local recovery also keeps pasted images out of cross-tab storage events. */
export function readDraft<T>(key: string): T | null {
	try {
		return JSON.parse(sessionStorage.getItem(`bob:${key}`) || "null");
	} catch {
		return null;
	}
}

export function writeDraft(key: string, value: unknown) {
	try {
		if (value === null) sessionStorage.removeItem(`bob:${key}`);
		else sessionStorage.setItem(`bob:${key}`, JSON.stringify(value));
	} catch {
		// Storage can be disabled or full (notably for pasted images). Keep the in-memory draft.
	}
}
