import type { MenuStep } from "@/components/ai/commandMenu";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";

export type SlashCommand = RegistryItem & {
	description: string;
	icon: string;
	aliases?: string[];
	/** `arg` is whatever follows the command, e.g. "glm" in "/model glm" */
	run: (arg: string) => MenuStep | Promise<MenuStep>;
};

/** Bob's "/" commands. Built-ins and extensions register through the same call. */
export const slashCommands = createRegistry<SlashCommand>();
