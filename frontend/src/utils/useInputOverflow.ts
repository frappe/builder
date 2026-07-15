import { ref, type Ref } from "vue";

/**
 * Tracks whether the text inside a control's nested `<input>` overflows its
 * visible width, used to show an edge fade on truncated values.
 */
export function useInputOverflow(containerRef: Ref<HTMLElement | null>) {
	const hasOverflow = ref(false);

	const checkOverflow = () => {
		const input = containerRef.value?.querySelector("input");
		hasOverflow.value = !!input && input.scrollWidth > input.clientWidth;
	};

	return { hasOverflow, checkOverflow };
}
