<template>
	<div class="select-none space-y-4">
		<!-- Type & Angle -->
		<div class="flex items-center gap-3">
			<TabButtons
				:buttons="[
					{ label: 'Linear', value: 'linear-gradient' },
					{ label: 'Radial', value: 'radial-gradient' },
				]"
				:modelValue="gradient.type"
				@update:modelValue="updateType"
				class="flex-1" />
			<div v-if="gradient.type === 'linear-gradient'" class="flex items-center gap-2">
				<AnglePicker :modelValue="parseInt(angleValue)" @update:modelValue="updateAngle" />
				<Input
					type="text"
					:modelValue="angleValue"
					@update:modelValue="updateAngle"
					:hideClearButton="true"
					class="w-13 [&>div>input]:pl-1.5 [&>div>input]:pr-4"
					placeholder="0">
					<template #suffix>
						<span class="absolute right-2 top-1/2 -translate-y-1/2 text-[12px] text-ink-gray-4">°</span>
					</template>
				</Input>
			</div>
		</div>

		<!-- Gradient Preview / Stop Bar -->
		<div
			class="shadow-inner relative h-5 w-full rounded border border-outline-gray-2"
			:style="barPreviewStyle"
			ref="barRef">
			<div class="absolute inset-0 cursor-copy" @click.self="addStopAtX"></div>
			<div
				v-for="(stop, index) in gradient.stops"
				:key="index"
				class="absolute top-1/2 z-10 -translate-x-1/2 -translate-y-1/2"
				:style="{ left: stop.position + '%' }">
				<Popover placement="top" :offset="10">
					<template #target="{ togglePopover }">
						<div
							class="size-4 cursor-pointer rounded-full border-2 border-white shadow-md ring-1 ring-black/20 transition-transform hover:scale-110 focus:outline-none"
							:style="{ backgroundColor: stop.color }"
							@mousedown="handleStopMouseDown(index, $event)"
							@click="(e) => !hasMoved && togglePopover()" />
					</template>
					<template #body="{ close }">
						<div class="rounded-lg border border-outline-gray-2 bg-surface-white p-3 shadow-xl">
							<ColorPicker
								renderMode="inline"
								:showInput="true"
								:modelValue="stop.color"
								@update:modelValue="(val) => updateStopColor(index, val)" />
							<div class="mt-2 flex items-center gap-2">
								<BuilderButton
									variant="subtle"
									label="Remove Stop"
									class="w-full"
									:disabled="gradient.stops.length <= 2"
									@click="
										() => {
											close();
											removeStop(index);
										}
									" />
							</div>
						</div>
					</template>
				</Popover>
			</div>
		</div>

		<!-- Presets -->
		<div class="flex flex-wrap gap-2">
			<div
				v-for="preset in presets"
				:key="preset.name"
				class="size-6 cursor-pointer rounded-full border border-outline-gray-2 shadow-sm transition-colors hover:border-outline-gray-4"
				:style="{ background: preset.gradient }"
				@click="applyPreset(preset.gradient)"
				:title="preset.name" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { parseGradient, stringifyGradient, type Gradient, type GradientStop } from "@/utils/gradientUtils";
import { useMouseInElement, useMousePressed } from "@vueuse/core";
import { Popover } from "frappe-ui";
import { computed, ref, watch } from "vue";
import AnglePicker from "./AnglePicker.vue";
import BuilderButton from "./BuilderButton.vue";
import ColorPicker from "./ColorPicker.vue";
import Input from "./Input.vue";
import TabButtons from "./TabButtons.vue";

const props = defineProps<{
	modelValue: string | null;
}>();

const emit = defineEmits(["update:modelValue"]);

const barRef = ref<HTMLElement | null>(null);
const draggingIdx = ref<number | null>(null);
const hasMoved = ref(false);

const { elementX } = useMouseInElement(barRef);
const { pressed } = useMousePressed();

const startDraggingX = ref(0);
const handleStopMouseDown = (index: number, e: MouseEvent) => {
	draggingIdx.value = index;
	hasMoved.value = false;
	startDraggingX.value = elementX.value;
};

watch([elementX, pressed], () => {
	if (!pressed.value) {
		draggingIdx.value = null;
		return;
	}

	if (draggingIdx.value === null || !barRef.value) return;

	if (Math.abs(elementX.value - startDraggingX.value) > 3) {
		hasMoved.value = true;
	}

	const position = Math.round(Math.max(0, Math.min(100, (elementX.value / barRef.value.clientWidth) * 100)));
	updateStopPosition(draggingIdx.value, position);
});

const presets = [
	{ name: "Hyper", gradient: "linear-gradient(135deg, #0cebeb 0%, #20e3b2 50%, #29ffc6 100%)" },
	{ name: "Ocean", gradient: "linear-gradient(135deg, #2b5876 0%, #4e4376 100%)" },
	{ name: "Sunkist", gradient: "linear-gradient(135deg, #f2994a 0%, #f2c94c 100%)" },
	{ name: "Skyline", gradient: "linear-gradient(135deg, #1488cc 0%, #2b32b2 100%)" },
	{ name: "Lush", gradient: "linear-gradient(135deg, #a8ff78 0%, #78ffd6 100%)" },
	{ name: "Purple Bliss", gradient: "linear-gradient(135deg, #360033 0%, #0b8793 100%)" },
	{ name: "Sunset", gradient: "linear-gradient(135deg, #ee0979 0%, #ff6a00 100%)" },
	{ name: "Dusk", gradient: "linear-gradient(135deg, #ffd89b 0%, #19033d 100%)" },
	{ name: "Cosmic", gradient: "linear-gradient(135deg, #ff00cc 0%, #333399 100%)" },
	{ name: "Clean Mirror", gradient: "linear-gradient(135deg, #e3e3e3 0%, #5d6d7e 100%)" },
	{ name: "Neon Glow", gradient: "radial-gradient(circle at center, #00f260 0%, #0575e6 100%)" },
	{ name: "Soft Radial", gradient: "radial-gradient(circle at center, #ff9a9e 0%, #fecfef 100%)" },
	{ name: "Deep Ocean", gradient: "radial-gradient(circle at center, #2b5876 0%, #4e4376 100%)" },
	{ name: "Royal", gradient: "linear-gradient(135deg, #141e30 0%, #243b55 100%)" },
];

const applyPreset = (presetGradient: string) => {
	const parsed = parseGradient(presetGradient);
	if (parsed) {
		gradient.value = parsed;
		emit("update:modelValue", stringifyGradient(parsed));
	}
};

const getDefaultGradient = (): Gradient => ({
	type: "linear-gradient",
	angle: "180deg",
	stops: [
		{ color: "#ffffff", position: 0 },
		{ color: "#000000", position: 100 },
	],
});

const gradient = ref<Gradient>(getDefaultGradient());

const initializeGradient = (value: string | null) => {
	const parsed = parseGradient(value || "");
	if (parsed) {
		gradient.value = parsed;
	} else if (!gradient.value.stops.length || !value) {
		gradient.value = getDefaultGradient();
	}
};

initializeGradient(props.modelValue);

const angleValue = computed(() => {
	return gradient.value.angle.replace("deg", "");
});

const barPreviewStyle = computed(() => {
	const stops = [...gradient.value.stops]
		.sort((a, b) => a.position - b.position)
		.map((s) => `${s.color} ${s.position}%`)
		.join(", ");
	return {
		background: `linear-gradient(to right, ${stops})`,
	};
});

const previewStyle = computed(() => {
	return {
		background: stringifyGradient(gradient.value),
	};
});

watch(
	() => props.modelValue,
	(newVal) => {
		const parsed = parseGradient(newVal || "");
		if (parsed) {
			const currentString = stringifyGradient(gradient.value);
			const newString = stringifyGradient(parsed);
			if (currentString !== newString) {
				gradient.value = parsed;
			}
		}
	},
);

const emitUpdate = () => {
	emit("update:modelValue", stringifyGradient(gradient.value));
};

const updateType = (type: any) => {
	gradient.value.type = type;
	if (type === "radial-gradient") {
		// Reset to valid radial config if it was a linear angle
		if (gradient.value.angle.includes("deg") || gradient.value.angle.includes("to ")) {
			gradient.value.angle = "circle at center";
		}
	} else {
		// Reset to valid linear angle if it was a radial config
		if (!gradient.value.angle.includes("deg")) {
			gradient.value.angle = "180deg";
		}
	}
	emitUpdate();
};

const updateAngle = (val: string | number) => {
	gradient.value.angle = (val + "").replace("deg", "") + "deg";
	emitUpdate();
};

const updateStopColor = (index: number, color: any) => {
	gradient.value.stops[index].color = color;
	emitUpdate();
};

const updateStopPosition = (index: number, position: number) => {
	const clampedPosition = Math.max(0, Math.min(100, Math.round(position)));
	gradient.value.stops[index].position = clampedPosition;
	emitUpdate();
};

const removeStop = (index: number) => {
	if (gradient.value.stops.length > 2) {
		gradient.value.stops.splice(index, 1);
		emitUpdate();
	}
};

const addStop = () => {
	const lastStop = gradient.value.stops[gradient.value.stops.length - 1];
	gradient.value.stops.push({
		color: lastStop.color,
		position: Math.min(100, lastStop.position + 10),
	});
	emitUpdate();
};

const addStopAtX = (e: MouseEvent) => {
	if (!barRef.value) return;
	const rect = barRef.value.getBoundingClientRect();
	const x = e.clientX - rect.left;
	const position = Math.round(Math.max(0, Math.min(100, (x / rect.width) * 100)));

	// Find where to insert
	const insertIdx = gradient.value.stops.findIndex((s) => s.position > position);
	const newStop: GradientStop = {
		color: "#ffffff",
		position,
	};

	if (insertIdx === -1) {
		gradient.value.stops.push(newStop);
	} else {
		gradient.value.stops.splice(insertIdx, 0, newStop);
	}
	gradient.value.stops.sort((a, b) => a.position - b.position);
	emitUpdate();
};
</script>
