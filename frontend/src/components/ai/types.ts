export interface AIModel {
	name: string;
	label: string;
	vision?: boolean;
	/** Has a usable key — its provider's own, or the shared one in Builder Settings. */
	ready?: boolean;
}

export interface AIProvider {
	provider: string;
	models: AIModel[];
}

/** One entry of a turn's timeline (see the event contract in agent/loop.py):
 * the model thinking, a tool running, or narration it wrote between rounds. */
export interface AITurnStep {
	id: number;
	kind: "thinking" | "tool" | "text";
	status?: "running" | "done";
	/** Tool steps: the human line ("Read block: Hero"). */
	summary?: string;
	/** Narration, or the model's reasoning when the provider streams it. */
	text?: string;
	tool?: string;
	ms?: number;
}

export interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
	message_type?: string;
	task_type?: string | null;
	block_id?: string | null;
	created_at?: string;
	metadata?: Record<string, any>;
}

export interface AffectedBlock {
	block_id: string;
	blockName: string;
	element: string;
	changedProps: string[];
}

export interface AffectedScript {
	script_name: string;
	changedProps: string[];
}
