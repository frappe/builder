import { slashCommands } from "@/components/ai/slashCommands";

export type CommandPanel = "model" | "credits" | "providers" | "chats";

type BobActions = {
	openPanel: (panel: CommandPanel, arg?: string) => void;
	newSession: () => void;
};

/** Bob's built-in "/" commands. Returns the unregister for when the chat panel unmounts. */
export function registerBobCommands(actions: BobActions): () => void {
	const unregisters = [
		slashCommands.register({
			name: "model",
			description: "Switch model",
			icon: "lucide-cpu",
			run: (arg) => actions.openPanel("model", arg),
		}),
		slashCommands.register({
			name: "credits",
			aliases: ["usage"],
			description: "See what's left on each provider",
			icon: "lucide-wallet",
			run: () => actions.openPanel("credits"),
		}),
		slashCommands.register({
			name: "providers",
			aliases: ["connect", "setup"],
			description: "Connect providers and manage models",
			icon: "lucide-server",
			run: () => actions.openPanel("providers"),
		}),
		slashCommands.register({
			name: "chats",
			aliases: ["history", "resume"],
			description: "Switch to another chat on this page",
			icon: "lucide-history",
			run: () => actions.openPanel("chats"),
		}),
		slashCommands.register({
			name: "new",
			aliases: ["clear"],
			description: "Start a new chat",
			icon: "lucide-plus",
			run: actions.newSession,
		}),
	];
	return () => unregisters.forEach((unregister) => unregister());
}
