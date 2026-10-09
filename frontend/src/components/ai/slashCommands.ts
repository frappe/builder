import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import { computed, ref, watch, type Ref } from "vue";

export type SlashCommand = RegistryItem & {
	description: string;
	icon: string;
	aliases?: string[];
	/** whatever follows the command, e.g. "kimi" in "/model kimi" */
	run: (arg: string) => void;
};

/** Bob's "/" commands. Built-ins and extensions register through the same call. */
export const slashCommands = createRegistry<SlashCommand>();

/** The "/" menu over a prompt: what matches, which row is highlighted, and the keys that drive it. */
export function useSlashMenu(prompt: Ref<string>) {
	const activeIndex = ref(0);
	const dismissed = ref(false);

	const typed = computed(() => parseSlash(prompt.value));
	const matches = computed(() => (typed.value ? matchingCommands(typed.value) : []));
	const isOpen = computed(() => !dismissed.value && matches.value.length > 0);

	watch(prompt, () => {
		activeIndex.value = 0;
		dismissed.value = false;
	});

	function run(command: SlashCommand) {
		const arg = typed.value?.arg ?? "";
		prompt.value = "";
		command.run(arg);
	}

	/** Send runs the highlighted command instead of sending "/model" to Bob as a prompt. */
	function runHighlighted(): boolean {
		if (!isOpen.value) return false;
		run(matches.value[activeIndex.value]);
		return true;
	}

	function onKeydown(event: KeyboardEvent) {
		if (!isOpen.value) return;
		if (event.key === "ArrowDown" || event.key === "ArrowUp") {
			event.preventDefault();
			move(event.key === "ArrowDown" ? 1 : -1);
		} else if (
			event.key === "Tab" ||
			(event.key === "Enter" && !event.shiftKey && !event.metaKey && !event.ctrlKey)
		) {
			event.preventDefault();
			runHighlighted();
		} else if (event.key === "Escape") {
			// the canvas also listens for Escape and would clear the selection
			event.preventDefault();
			event.stopPropagation();
			dismissed.value = true;
		}
	}

	function move(step: number) {
		const count = matches.value.length;
		activeIndex.value = (activeIndex.value + step + count) % count;
	}

	return { matches, activeIndex, isOpen, run, runHighlighted, onKeydown };
}

type TypedCommand = { name: string; arg: string; hasArg: boolean };

function parseSlash(text: string): TypedCommand | null {
	const match = /^\/([\w-]*)(\s+([^\n]*))?$/.exec(text);
	if (!match) return null;
	return { name: match[1].toLowerCase(), arg: (match[3] || "").trim(), hasArg: match[2] !== undefined };
}

function matchingCommands({ name, hasArg }: TypedCommand): SlashCommand[] {
	// once an argument follows, only the exact command it belongs to still applies
	return slashCommands.visible.value.filter((command) =>
		commandNames(command).some((n) => (hasArg ? n === name : n.startsWith(name))),
	);
}

const commandNames = (command: SlashCommand) => [command.name, ...(command.aliases || [])];
