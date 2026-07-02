import { useCanvasHistory } from "@/utils/useCanvasHistory";
import { Ref } from "vue";

export interface BreakpointConfig {
	icon: string;
	device: "desktop" | "tablet" | "mobile";
	displayName: string;
	width: number;
	visible: boolean;
	renderedOnce: boolean;
}

export interface CanvasProps {
	background: string;
	scale: number;
	translateX: number;
	translateY: number;
	settingCanvas: boolean;
	scaling: boolean;
	panning: boolean;
	breakpoints: BreakpointConfig[];
	frameRoots?: Map<string, HTMLElement>;
}

export type CanvasHistory = Ref<ReturnType<typeof useCanvasHistory>>;
