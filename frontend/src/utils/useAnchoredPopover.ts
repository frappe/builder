import { ref } from "vue";

/**
 * State for a popover anchored to a whole control row (a swatch beside an input).
 *
 * frappe-ui's `#trigger` toggles on every click inside it, which for a row means
 * focusing the input would open and close the panel. Bind `:open` and
 * `@update:open` here instead: the row decides when it opens (a swatch click, a
 * focus), while dismissals from outside the row still close it.
 */
export function useAnchoredPopover(onChange?: (open: boolean) => void) {
	const isOpen = ref(false);
	// true for the duration of a click inside the anchor: the toggle the trigger
	// emits for that click is ignored, a dismissal (outside click, Escape) is not
	let anchorClick = false;

	const set = (value: boolean) => {
		if (isOpen.value === value) return;
		isOpen.value = value;
		onChange?.(value);
	};

	const open = () => set(true);
	const close = () => set(false);
	const toggle = (value?: boolean | Event) => {
		if (value instanceof Event || value == null) value = !isOpen.value;
		set(value);
	};

	const onAnchorClick = () => {
		anchorClick = true;
		setTimeout(() => {
			anchorClick = false;
		});
	};

	const onUpdateOpen = (value: boolean) => {
		if (value || anchorClick) return;
		close();
	};

	return { isOpen, open, close, toggle, onAnchorClick, onUpdateOpen };
}
