export interface AIModel {
	name: string;
	label: string;
	vision?: boolean;
}

export interface AIProvider {
	provider: string;
	models: AIModel[];
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

/** One client-side operation emitted by the agent's `ai_chat_tool_batch` event. */
export interface ToolOperation {
	tool_name: string;
	args: Record<string, any>;
}
