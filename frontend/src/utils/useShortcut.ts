import { isCtrlOrCmd, isTargetEditable } from "@/utils/helpers";
import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, readonly } from "vue";

export interface ShortcutConfig {
	/** Shortcut key(s) to listen for (e.g. "s", "Escape", "ArrowUp") */
	key: string;
	/** Whether Ctrl (or Cmd on Mac) must be held */
	ctrl?: boolean;
	/** Whether Shift must be held */
	shift?: boolean;
	/** Human-readable label for the shortcut */
	description: string;
	/** Group name for categorizing in the shortcuts modal */
	group?: string;
	/** Handler to execute when the shortcut is triggered */
	handler: (e: KeyboardEvent) => void;
	/** Whether to prevent default browser behavior (default: true) */
	preventDefault?: boolean;
	/** Whether the shortcut should work when an input/textarea is focused (default: false) */
	allowInInput?: boolean;
	/**
	 * Condition function - shortcut only fires when this returns true.
	 * If not provided, the shortcut is always active.
	 */
	condition?: () => boolean;
}

export interface RegisteredShortcut {
	key: string;
	ctrl: boolean;
	shift: boolean;
	description: string;
	group: string;
	id: symbol;
	condition?: () => boolean;
}

const activeShortcuts = reactive<RegisteredShortcut[]>([]);
const shortcutHandlers = new Map<symbol, ShortcutConfig>();

let listenerAttached = false;

function isDialogOpen() {
	return !!document.querySelector("[role='dialog']");
}

function attachGlobalListener() {
	if (listenerAttached) return;
	listenerAttached = true;

	document.addEventListener("keydown", globalKeydownHandler);
}

function globalKeydownHandler(e: KeyboardEvent) {
	if (isDialogOpen()) return;

	// Iterate through all registered shortcuts and find matching ones
	for (const [id, config] of shortcutHandlers) {
		if (!matchesShortcut(e, config)) continue;

		// Check condition
		if (config.condition && !config.condition()) continue;

		// Check if target is an editable field
		if (!config.allowInInput && isTargetEditable(e)) continue;

		if (config.preventDefault !== false) {
			e.preventDefault();
		}

		config.handler(e);
		return; // Only fire the first match
	}
}

function matchesShortcut(e: KeyboardEvent, config: ShortcutConfig): boolean {
	if (e.key.toLowerCase() !== config.key.toLowerCase() && e.key !== config.key) {
		return false;
	}

	const wantsCtrl = config.ctrl ?? false;
	const wantsShift = config.shift ?? false;

	if (wantsCtrl && !isCtrlOrCmd(e)) return false;
	if (!wantsCtrl && isCtrlOrCmd(e)) return false;

	// For keys that are themselves produced by Shift (like ? = Shift+/),
	// only enforce the shift check when shift is explicitly specified in the config
	const isShiftProducedKey =
		config.key !== config.key.toLowerCase() || /^[?!@#$%^&*()_+{}|:"<>~]$/.test(config.key);
	if (wantsShift && !e.shiftKey) return false;
	if (!wantsShift && e.shiftKey && !isShiftProducedKey) return false;

	return true;
}

function formatShortcutLabel(config: { key: string; ctrl?: boolean; shift?: boolean }): string {
	const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
	const parts: string[] = [];

	if (config.ctrl) {
		parts.push(isMac ? "⌘" : "Ctrl");
	}
	if (config.shift) {
		parts.push(isMac ? "⇧" : "Shift");
	}

	// Friendly key names
	const keyMap: Record<string, string> = {
		arrowup: "↑",
		arrowdown: "↓",
		arrowleft: "←",
		arrowright: "→",
		escape: "Esc",
		backspace: "⌫",
		delete: "Del",
		enter: "↵",
		" ": "Space",
		"\\": "\\",
		"=": "+",
		"-": "−",
	};

	const displayKey = keyMap[config.key.toLowerCase()] ?? config.key.toUpperCase();
	parts.push(displayKey);

	return parts.join(isMac ? " " : " + ");
}

/**
 * Register keyboard shortcuts that are automatically cleaned up when the component unmounts.
 * Returns the list of all active shortcuts across the app.
 *
 * @example
 * const { activeShortcuts } = useShortcut([
 *   { key: "s", ctrl: true, description: "Save", group: "General", handler: () => save() },
 *   { key: "z", ctrl: true, description: "Undo", group: "Edit", handler: () => undo() },
 * ]);
 */
export function useShortcut(shortcuts: ShortcutConfig | ShortcutConfig[]) {
	attachGlobalListener();

	const configs = Array.isArray(shortcuts) ? shortcuts : [shortcuts];
	const registeredIds: symbol[] = [];

	for (const config of configs) {
		const id = Symbol(config.description);
		const registered: RegisteredShortcut = {
			key: config.key,
			ctrl: config.ctrl ?? false,
			shift: config.shift ?? false,
			description: config.description,
			group: config.group ?? "General",
			id,
			condition: config.condition,
		};

		shortcutHandlers.set(id, config);
		activeShortcuts.push(registered);
		registeredIds.push(id);
	}

	const removeShortcuts = () => {
		for (const id of registeredIds) {
			shortcutHandlers.delete(id);
			const idx = activeShortcuts.findIndex((s) => s.id === id);
			if (idx !== -1) activeShortcuts.splice(idx, 1);
		}
	};

	const addShortcuts = () => {
		for (let i = 0; i < configs.length; i++) {
			const id = registeredIds[i];
			if (!shortcutHandlers.has(id)) {
				shortcutHandlers.set(id, configs[i]);
				activeShortcuts.push({
					key: configs[i].key,
					ctrl: configs[i].ctrl ?? false,
					shift: configs[i].shift ?? false,
					description: configs[i].description,
					group: configs[i].group ?? "General",
					id,
					condition: configs[i].condition,
				});
			}
		}
	};

	// Clean up on component unmount
	onBeforeUnmount(removeShortcuts);

	// Handle keep-alive: remove shortcuts when deactivated, re-add when activated
	onDeactivated(removeShortcuts);
	onActivated(addShortcuts);

	return {
		activeShortcuts: readonly(activeShortcuts),
		formatShortcutLabel,
	};
}

/**
 * Get all currently registered shortcuts whose conditions are met (read-only).
 */
export function getActiveShortcuts() {
	return computed(() => activeShortcuts.filter((s) => !s.condition || s.condition()));
}

export { formatShortcutLabel };
