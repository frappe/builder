export interface AIModel {
	name: string;
	label: string;
	vision?: boolean;
	/** Has a usable key — its provider's own, or the shared one in Builder Settings. */
	ready?: boolean;
	/** Set for a gateway with its own base URL, the only kind that can report credits. */
	api_base?: string | null;
}

export interface AIProvider {
	provider: string;
	models: AIModel[];
}

/** A provider the setup flow offers (presets.public_preset). */
export interface AIPreset {
	id: string;
	name: string;
	tagline: string;
	blurb: string;
	key_url: string;
	key_prefix: string;
	key_steps: string[];
	api_base: string | null;
	custom: boolean;
	oauth: boolean;
	has_key: boolean;
	needs_name: boolean;
	needs_api_base: boolean;
	configured: boolean;
	models: { model_id: string; label: string; note: string; recommended: boolean }[];
}

/** What builder.ai.api.ai_setup_state reports. */
export interface AISetupState {
	configured: boolean;
	models: number;
	providers: number;
	needs_migrate?: boolean;
	presets: AIPreset[];
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
