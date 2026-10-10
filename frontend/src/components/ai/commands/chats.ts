import type { MenuItem, MenuLevel } from "@/components/ai/commandMenu";
import type { BobContext } from "@/components/ai/commands/shared";

export function chatsLevel(ctx: BobContext): MenuLevel {
	const { chat } = ctx;
	return {
		title: "Chats",
		items: () => [
			...chat.sessions.value.map((session): MenuItem => ({
				key: session.name,
				label: session.title || "New chat",
				group: "On this page",
				selected: session.name === chat.sessionId.value,
				run: () => chat.switchSession(session.name),
			})),
			{ key: "new", label: "New chat", icon: "lucide-plus", run: () => chat.newSession() },
			...(chat.sessionId.value
				? [
						{
							key: "delete",
							label: "Delete this chat",
							icon: "lucide-trash-2",
							theme: "red" as const,
							run: () => chat.deleteSession(),
						},
					]
				: []),
		],
	};
}
