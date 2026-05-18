import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import type { CanvasProps } from "@/types/Builder/BuilderCanvas";
import { computed, reactive, ref, type Ref } from "vue";

const MIN_MARQUEE_DRAG = 5;
const OVERLAP_SELECTION_THRESHOLD = 0.5;

type UseCanvasMarqueeSelectionOptions = {
	canvasContainer: Ref<HTMLElement | null>;
	canvasProps: CanvasProps;
	activeBreakpoint: Ref<string | null>;
	selectedBlockIds: Ref<Set<string>>;
	findBlock: (id: string) => Block | null;
	setActiveBreakpoint: (breakpoint: string | null) => void;
	setHoveredBreakpoint: (breakpoint: string | null) => void;
};

export function useCanvasMarqueeSelection(options: UseCanvasMarqueeSelectionOptions) {
	const {
		canvasContainer,
		canvasProps,
		activeBreakpoint,
		selectedBlockIds,
		findBlock,
		setActiveBreakpoint,
		setHoveredBreakpoint,
	} = options;

	const builderStore = useBuilderStore();
	const canvasStore = useCanvasStore();
	const suppressNextClick = ref(false);
	const marqueeAdditiveSelection = ref(false);
	const marqueeBreakpoint = ref<string | null>(null);
	const marqueeInitialSelection = ref<Set<string>>(new Set());
	const marquee = reactive({
		active: false,
		visible: false,
		startX: 0,
		startY: 0,
		currentX: 0,
		currentY: 0,
	});

	const marqueeStyle = computed(() => {
		const left = Math.min(marquee.startX, marquee.currentX);
		const top = Math.min(marquee.startY, marquee.currentY);
		const width = Math.abs(marquee.currentX - marquee.startX);
		const height = Math.abs(marquee.currentY - marquee.startY);

		return {
			left: `${left}px`,
			top: `${top}px`,
			width: `${width}px`,
			height: `${height}px`,
			border: "1px solid rgba(59, 130, 246, 0.85)",
			background: "rgba(59, 130, 246, 0.12)",
		};
	});

	const removeWindowListeners = () => {
		window.removeEventListener("mousemove", handleMarqueeMove);
		window.removeEventListener("mouseup", handleMarqueeEnd);
	};

	const handleMarqueeStart = (ev: MouseEvent) => {
		if (!shouldStartMarquee(ev)) {
			return;
		}

		marquee.active = true;
		marquee.visible = false;
		marquee.startX = ev.clientX;
		marquee.startY = ev.clientY;
		marquee.currentX = ev.clientX;
		marquee.currentY = ev.clientY;
		marqueeAdditiveSelection.value = ev.shiftKey || ev.metaKey || ev.ctrlKey;
		marqueeInitialSelection.value = new Set(selectedBlockIds.value);
		marqueeBreakpoint.value = getBreakpointAtPoint(ev.clientX, ev.clientY);

		window.addEventListener("mousemove", handleMarqueeMove);
		window.addEventListener("mouseup", handleMarqueeEnd);
	};

	const handleMarqueeMove = (ev: MouseEvent) => {
		if (!marquee.active) {
			return;
		}

		marquee.currentX = ev.clientX;
		marquee.currentY = ev.clientY;

		if (!marquee.visible) {
			const deltaX = Math.abs(marquee.currentX - marquee.startX);
			const deltaY = Math.abs(marquee.currentY - marquee.startY);
			marquee.visible = deltaX >= MIN_MARQUEE_DRAG || deltaY >= MIN_MARQUEE_DRAG;
		}

		if (marquee.visible) {
			ev.preventDefault();
			applyMarqueeSelection();
		}
	};

	const handleMarqueeEnd = () => {
		if (!marquee.active) {
			return;
		}

		removeWindowListeners();

		if (marquee.visible) {
			applyMarqueeSelection();
			suppressNextClick.value = true;
		}

		marquee.active = false;
		marquee.visible = false;
	};

	const shouldStartMarquee = (ev: MouseEvent) => {
		if (ev.button !== 0) return false;
		if (builderStore.mode !== "select") return false;
		if (builderStore.readOnlyMode) return false;
		if (canvasStore.isDragging || canvasProps.panning || canvasProps.scaling) return false;

		const target = ev.target as HTMLElement | null;
		if (!target) return false;

		if (target.closest("input, textarea, select, button, a, [contenteditable='true'], .editor")) {
			return false;
		}

		if (target.closest("[data-block-id]:not([data-block-id='root'])")) {
			return false;
		}

		return true;
	};

	const getBreakpointAtPoint = (x: number, y: number) => {
		const container = canvasContainer.value;
		if (!container) {
			return activeBreakpoint.value;
		}

		const canvases = Array.from(container.querySelectorAll(".canvas[data-breakpoint]")) as HTMLElement[];

		for (const canvasElement of canvases) {
			const rect = canvasElement.getBoundingClientRect();
			if (!rect.width || !rect.height) continue;
			if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
				return canvasElement.dataset.breakpoint || activeBreakpoint.value;
			}
		}

		return activeBreakpoint.value;
	};

	const getMarqueeIntersectingBlockIds = () => {
		const container = canvasContainer.value;
		if (!container) return new Set<string>();

		const selectionRect = {
			left: Math.min(marquee.startX, marquee.currentX),
			right: Math.max(marquee.startX, marquee.currentX),
			top: Math.min(marquee.startY, marquee.currentY),
			bottom: Math.max(marquee.startY, marquee.currentY),
		};

		const targetBreakpoint = marqueeBreakpoint.value || activeBreakpoint.value;
		const blockElements = Array.from(
			container.querySelectorAll(".__builder_component__[data-block-id][data-breakpoint]"),
		) as HTMLElement[];
		const intersectingBlockIds = new Set<string>();
		const fullyContainedBlockIds = new Set<string>();

		for (const element of blockElements) {
			if ((element.dataset.breakpoint || null) !== targetBreakpoint) continue;

			const blockId = element.dataset.blockId;
			if (!blockId || blockId === "root") continue;

			const rect = element.getBoundingClientRect();
			if (!rect.width || !rect.height) continue;

			const intersects = !(
				rect.right < selectionRect.left ||
				rect.left > selectionRect.right ||
				rect.bottom < selectionRect.top ||
				rect.top > selectionRect.bottom
			);

			if (!intersects) continue;

			const intersectionWidth = Math.max(
				0,
				Math.min(rect.right, selectionRect.right) - Math.max(rect.left, selectionRect.left),
			);
			const intersectionHeight = Math.max(
				0,
				Math.min(rect.bottom, selectionRect.bottom) - Math.max(rect.top, selectionRect.top),
			);
			const intersectionArea = intersectionWidth * intersectionHeight;
			const elementArea = rect.width * rect.height;
			const overlapRatio = elementArea > 0 ? intersectionArea / elementArea : 0;

			const fullyContained =
				rect.left >= selectionRect.left &&
				rect.right <= selectionRect.right &&
				rect.top >= selectionRect.top &&
				rect.bottom <= selectionRect.bottom;

			if (!fullyContained && overlapRatio <= OVERLAP_SELECTION_THRESHOLD) continue;

			const selected = findBlock(blockId);
			if (selected) {
				intersectingBlockIds.add(selected.blockId);
				if (fullyContained) {
					fullyContainedBlockIds.add(selected.blockId);
				}
			}
		}

		const parentOnlyBlockIds = new Set<string>();

		for (const blockId of intersectingBlockIds) {
			const block = findBlock(blockId);
			if (!block) continue;

			let hasFullyContainedAncestor = false;
			let parent = block.getParentBlock();

			while (parent) {
				if (fullyContainedBlockIds.has(parent.blockId)) {
					hasFullyContainedAncestor = true;
					break;
				}
				parent = parent.getParentBlock();
			}

			if (!hasFullyContainedAncestor) {
				parentOnlyBlockIds.add(blockId);
			}
		}

		return parentOnlyBlockIds;
	};

	const applyMarqueeSelection = () => {
		const targetBreakpoint = marqueeBreakpoint.value || activeBreakpoint.value;
		const intersectingBlockIds = getMarqueeIntersectingBlockIds();
		const nextSelectedBlockIds = new Set<string>();

		if (marqueeAdditiveSelection.value) {
			marqueeInitialSelection.value.forEach((id) => nextSelectedBlockIds.add(id));
		}

		intersectingBlockIds.forEach((id) => nextSelectedBlockIds.add(id));
		selectedBlockIds.value = nextSelectedBlockIds;

		if (targetBreakpoint) {
			setActiveBreakpoint(targetBreakpoint);
			setHoveredBreakpoint(targetBreakpoint);
		}
	};

	return {
		marquee,
		marqueeStyle,
		suppressNextClick,
		handleMarqueeStart,
		cleanupMarqueeListeners: removeWindowListeners,
	};
}
