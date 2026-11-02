import type { AIRunEvent } from "./types";
import type { CardSubmission } from "./cardAnswers";

/** Journal events are contiguous; older servers still use unordered socket sequences. */
export class RunEvents {
	private runs = new Map<
		string,
		{ seen: Set<number>; finished: boolean; cursor: number; pending: Map<number, () => void> }
	>();

	accept(event: AIRunEvent, replay?: () => void) {
		if (!event.run_id || !Number.isInteger(event.seq)) return false;
		let run = this.runs.get(event.run_id);
		if (!run) {
			run = { seen: new Set(), finished: false, cursor: 0, pending: new Map() };
			this.runs.set(event.run_id, run);
		}
		if (run.finished || run.seen.has(event.seq)) return false;
		if (event.journal) {
			if (event.seq <= run.cursor) return false;
			if (event.seq > run.cursor + 1) {
				if (replay && run.pending.size < 500) run.pending.set(event.seq, replay);
				return false;
			}
			run.cursor = event.seq;
			run.pending.delete(event.seq);
			const next = run.pending.get(event.seq + 1);
			if (next) queueMicrotask(next);
			return true;
		}
		run.seen.add(event.seq);
		return true;
	}

	cursor(runId: string) {
		return this.runs.get(runId)?.cursor || 0;
	}

	finished(runId: string) {
		return this.runs.get(runId)?.finished ?? false;
	}

	finish(runId: string) {
		if (runId)
			this.runs.set(runId, {
				seen: new Set(),
				finished: true,
				cursor: this.cursor(runId),
				pending: new Map(),
			});
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
	cardAnswer?: CardSubmission | null;
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
