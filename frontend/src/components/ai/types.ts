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

/** A provider the connect menu offers (presets.public_preset). It names no models:
 * the server discovers those once the provider is connected. */
export interface AIPreset {
	id: string;
	name: string;
	tagline: string;
	key_url: string;
	key_prefix: string;
	oauth: boolean;
	custom: boolean;
	connected: boolean;
}

/** A provider just connected, and its models on offer, best first. */
export interface ConnectResult {
	provider: string;
	models: { name: string; label: string }[];
}

/** A model a provider serves that the picker doesn't offer yet (catalog.ProviderCatalog). */
export interface AddableModel {
	model_id: string;
	label: string;
	released?: string;
	context?: number;
	/** null when nothing describes the model */
	vision: boolean | null;
}

/** A started ChatGPT sign-in: the code to enter, where, and how often to ask about it. */
export interface DeviceSignIn {
	state: string;
	code: string;
	url: string;
	interval: number;
	message?: string;
}

/** The fallback ChatGPT sign-in: a link whose redirect the user pastes back. */
export interface BrowserSignIn {
	state: string;
	url: string;
}

export type SignInStatus =
	({ status: "connected" } & ConnectResult) | { status: "pending" | "failed" | "expired"; message?: string };

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
