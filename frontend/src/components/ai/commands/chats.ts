import type { MenuItem, MenuLevel } from "@/components/ai/commandMenu";
import type { BobContext } from "@/components/ai/commands/shared";

export function chatsLevel(ctx: BobContext): MenuLevel {
	const { chat } = ctx;
	return {
		title: "Chats",
		items: () => [
			{ key: "new", label: "New chat", icon: "lucide-plus", run: () => chat.newSession() },
			...chat.sessions.value.map((session): MenuItem => ({
				key: session.name,
				label: session.title || "New chat",
				checked: session.name === chat.sessionId.value,
				run: () => chat.switchSession(session.name),
			})),
			...(chat.sessionId.value
				? [
						{
							key: "delete",
							label: "Delete this chat",
							icon: "lucide-trash-2",
							danger: true,
							run: () => chat.deleteSession(),
						},
					]
				: []),
		],
	};
}
