import { slashCommands } from "@/components/ai/slashCommands";
import { getErrorMessage } from "@/utils/helpers";
import { computed, ref, shallowRef, watch, type Ref } from "vue";

/** One row, in frappe-ui menu terms: the description sits under the label, and the
 * suffix is a tick (selected), a switch (switchValue) or a chevron (submenu). */
export type MenuItem = {
	key: string;
	label: string;
	description?: string;
	icon?: string;
	/** the current choice, like the model in use */
	selected?: boolean;
	/** an on/off row; choosing it flips the value */
	switchValue?: boolean;
	/** choosing it opens another level */
	submenu?: boolean;
	theme?: "red";
	group?: string;
	run: () => MenuStep | Promise<MenuStep>;
};

/** A level is a list to pick from, or a single field to fill in (an API key, a URL). */
export type MenuLevel = {
	title: string;
	note?: string;
	/** starts the list filtered, e.g. "glm" for "/model glm" */
	query?: string;
	items?: () => MenuItem[] | Promise<MenuItem[]>;
	input?: { placeholder: string; secret?: boolean; submit: (value: string) => MenuStep | Promise<MenuStep> };
	empty?: string;
	/** for a level that waits on something outside the menu, like a sign-in tab; returns its cleanup */
	start?: (menu: CommandMenu) => (() => void) | void;
};

/** What a choice leads to: a deeper level, this level again (re-read), the one above
 * (or several, after deleting what the level showed), or closing. */
export type MenuStep = MenuLevel | "stay" | "back" | { back: number } | void;

export type CommandMenu = ReturnType<typeof useCommandMenu>;

/** The "/" menu over the composer. Typing "/" lists the commands; a command can open
 * levels of its own, and the composer text filters whichever list is showing. */
export function useCommandMenu(prompt: Ref<string>) {
	const stack = shallowRef<MenuLevel[]>([]);
	const items = shallowRef<MenuItem[]>([]);
	const note = ref("");
	const noteIsError = ref(false);
	const busy = ref(false);
	const activeIndex = ref(0);
	const dismissed = ref(false);
	let stopLevel: (() => void) | void;

	const level = computed(() => stack.value.at(-1) ?? null);
	const typed = computed(() => (stack.value.length ? null : parseSlash(prompt.value)));
	const rootItems = computed(() => (typed.value ? commandItems(typed.value) : []));
	const visibleItems = computed(() =>
		level.value ? filterItems(items.value, prompt.value) : rootItems.value,
	);
	const isOpen = computed(() => !!level.value || (!dismissed.value && rootItems.value.length > 0));

	watch(prompt, () => {
		activeIndex.value = 0;
		if (!level.value) dismissed.value = false;
	});

	async function open(next: MenuLevel) {
		stack.value = [...stack.value, next];
		await enter();
	}

	async function replace(next: MenuLevel) {
		stack.value = [...stack.value.slice(0, -1), next];
		await enter();
	}

	async function back(levels = 1) {
		stopLevel?.();
		stack.value = stack.value.slice(0, -levels);
		if (!stack.value.length) return close();
		await enter();
	}

	function close() {
		stopLevel?.();
		// inside a level the composer text was the menu's filter, never a prompt
		if (stack.value.length || prompt.value.startsWith("/")) prompt.value = "";
		stack.value = [];
		items.value = [];
		note.value = "";
	}

	async function enter() {
		stopLevel?.();
		prompt.value = level.value?.query ?? "";
		activeIndex.value = 0;
		setNote(level.value?.note ?? "");
		stopLevel = level.value?.start?.(menu);
		await reload();
	}

	async function reload() {
		const current = level.value;
		if (!current?.items) return void (items.value = []);
		busy.value = true;
		try {
			const loaded = await current.items();
			if (level.value === current) items.value = loaded;
		} catch (error) {
			setNote(getErrorMessage(error, "Could not load this list"), true);
		} finally {
			busy.value = false;
		}
	}

	async function choose(item: MenuItem) {
		await follow(() => item.run());
	}

	async function submit(value: string) {
		const input = level.value?.input;
		if (input) await follow(() => input.submit(value));
	}

	async function follow(step: () => MenuStep | Promise<MenuStep>) {
		busy.value = true;
		try {
			const next = await step();
			if (next === "stay") await reload();
			else if (next === "back") await back();
			else if (next && "back" in next) await back(next.back);
			else if (next) await open(next);
			else close();
		} catch (error) {
			setNote(getErrorMessage(error, "That didn't work"), true);
		} finally {
			busy.value = false;
		}
	}

	function setNote(text: string, isError = false) {
		note.value = text;
		noteIsError.value = isError;
	}

	/** Composer keys while the menu is open. Returns true when the menu took the key. */
	function onKeydown(event: KeyboardEvent) {
		if (!isOpen.value) return false;
		const count = visibleItems.value.length;
		if ((event.key === "ArrowDown" || event.key === "ArrowUp") && count) {
			activeIndex.value = (activeIndex.value + (event.key === "ArrowDown" ? 1 : -1) + count) % count;
		} else if (event.key === "Enter" || event.key === "Tab") {
			if (event.shiftKey) return false;
			const item = visibleItems.value[activeIndex.value];
			if (item) choose(item);
		} else if (event.key === "Escape") {
			if (level.value) back();
			else dismissed.value = true;
		} else if (event.key === "Backspace" && level.value && !prompt.value) {
			back();
		} else {
			return false;
		}
		event.preventDefault();
		// the canvas listens for Escape and Backspace too, and would act on the selection
		event.stopPropagation();
		return true;
	}

	const menu = {
		stack,
		level,
		visibleItems,
		note,
		noteIsError,
		busy,
		activeIndex,
		isOpen,
		open,
		replace,
		back,
		close,
		reload,
		choose,
		submit,
		setNote,
		onKeydown,
	};
	return menu;
}

type TypedCommand = { name: string; arg: string; hasArg: boolean };

function parseSlash(text: string): TypedCommand | null {
	const match = /^\/([\w-]*)(\s+([^\n]*))?$/.exec(text);
	if (!match) return null;
	return { name: match[1].toLowerCase(), arg: (match[3] || "").trim(), hasArg: match[2] !== undefined };
}

function commandItems({ name, arg, hasArg }: TypedCommand): MenuItem[] {
	// once an argument follows, only the exact command it belongs to still applies
	return slashCommands.visible.value
		.filter((c) => [c.name, ...(c.aliases || [])].some((n) => (hasArg ? n === name : n.startsWith(name))))
		.map((c) => ({
			key: c.name,
			label: `/${c.name}`,
			description: c.description,
			icon: c.icon,
			submenu: c.submenu,
			run: () => c.run(arg),
		}));
}

function filterItems(items: MenuItem[], query: string): MenuItem[] {
	const needle = query.trim().toLowerCase();
	if (!needle) return items;
	return items.filter((item) =>
		`${item.label} ${item.description ?? ""} ${item.group ?? ""}`.toLowerCase().includes(needle),
	);
}
