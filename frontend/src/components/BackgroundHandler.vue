<template>
	<Popover placement="left" class="!block w-full" :offset="25">
		<template #target="{ togglePopover }">
			<div class="flex w-full items-center justify-between" @focusin="updateActiveState">
				<StylePropertyControl
					propertyKey="background"
					:component="BackgroundInput"
					label="Background"
					:enableStates="true"
					:allowDynamicValue="true"
					placeholder="Set Background"
					readonly
					:selectOnFocus="false"
					class="[&_input]:cursor-pointer"
					@focus="togglePopover"
					:getModelValue="() => getDisplayValue(null)"
					:getVariantValue="(v: string) => getDisplayValue(v)"
					:setVariantValue="handleSetVariant"
					:setModelValue="(val: string) => setBGValue(val)">
					<template #prefix="{ variant }">
						<div
							class="absolute left-2 top-[6px] size-4 cursor-pointer rounded shadow-md"
							@click="
								() => {
									activeState = variant;
									togglePopover();
								}
							"
							:class="{ 'bg-surface-gray-4': !getHasBackground(variant) }"
							:style="getPreviewStyle(variant)" />
					</template>
				</StylePropertyControl>
			</div>
		</template>
		<template #body>
			<div
				class="background-popover-body w-64 rounded-lg border border-outline-gray-2 bg-surface-base p-3 shadow-xl">
				<TabButtons
					:buttons="[
						{ label: '', value: 'color', icon: 'lucide-droplet' },
						{ label: '', value: 'image', icon: 'lucide-image' },
						{ label: '', value: 'gradient', icon: 'lucide-aperture' },
					]"
					v-model="activeTab"
					class="mb-3" />

				<!-- Color Tab -->
				<div v-if="activeTab === 'color'" class="w-full space-y-4">
					<ColorPicker
						renderMode="inline"
						:modelValue="backgroundColor"
						:showInput="true"
						@update:modelValue="setBGColor" />
				</div>

				<!-- Image Tab -->
				<div v-else-if="activeTab === 'image'" class="space-y-4">
					<div
						class="image-preview group relative h-24 w-full cursor-pointer overflow-hidden rounded bg-surface-gray-3"
						:style="getPreviewStyle(activeState)">
						<FileUploader
							@success="setBGImage"
							:uploadArgs="{
								private: false,
								folder: 'Home/Builder Uploads',
								optimize: true,
								upload_endpoint: '/api/method/builder.api.upload_builder_asset',
							}">
							<template v-slot="{ openFileSelector }">
								<div
									class="absolute bottom-0 left-0 right-0 top-0 hidden place-items-center bg-gray-500 bg-opacity-20"
									:class="{
										'!grid': !backgroundImageURL,
										'group-hover:grid': backgroundImageURL,
									}">
									<Button @click="openFileSelector">Upload</Button>
								</div>
							</template>
						</FileUploader>
					</div>
					<div class="space-y-2">
						<InlineInput
							label="Size"
							:modelValue="backgroundSize"
							type="select"
							:options="sizeOptions"
							@update:modelValue="setBGSize" />
						<InlineInput
							label="Position"
							:modelValue="backgroundPosition"
							type="select"
							:options="positionOptions"
							@update:modelValue="setBGPosition" />
						<InlineInput
							label="Repeat"
							:modelValue="backgroundRepeat"
							type="select"
							:options="repeatOptions"
							@update:modelValue="setBGRepeat" />
					</div>
					<Button v-if="showServeLocallyButton" class="w-full" @click="serveBackgroundImageLocally">
						{{ serveLocallyButtonText }}
					</Button>
					<Button v-if="backgroundImageURL" class="w-full" variant="subtle" @click="clearBGImage">
						Clear Image
					</Button>
				</div>

				<!-- Gradient Tab -->
				<div v-else class="space-y-4">
					<GradientEditor :modelValue="rawBackgroundImage" @update:modelValue="setGradient" />
					<Button :disabled="!isGradient" class="w-full" variant="subtle" @click="clearBGImage">
						Clear Gradient
					</Button>
				</div>

				<div
					v-if="isTextBlock"
					class="flex items-center justify-between pt-3"
					:class="{
						'px-0.5': activeTab !== 'image',
					}">
					<InputLabel class="flex-1">Clip Background to Text</InputLabel>
					<Switch size="sm" :modelValue="backgroundClip === 'text'" @update:modelValue="setBGClip" />
				</div>
			</div>
		</template>
	</Popover>
</template>

<script lang="ts" setup>
import ColorPicker from "@/components/Controls/ColorPicker.vue";
import GradientEditor from "@/components/Controls/GradientEditor.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import Input from "@/components/Controls/Input.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import TabButtons from "@/components/Controls/TabButtons.vue";
import useBuilderStore from "@/stores/builderStore";
import blockController from "@/utils/blockController";
import { cssUrl } from "@/utils/helpers";
import { getOptimizeButtonText, optimizeImage, shouldShowOptimizeButton } from "@/utils/imageUtils";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { FileUploader, Popover, Switch } from "frappe-ui";
import { computed, defineComponent, h, ref, watch } from "vue";

const builderStore = useBuilderStore();
const { getVariableName, resolveVariableValue, variables } = useBuilderVariable();

// wraps Input to style the value like ColorInput does when it displays a variable name
const BackgroundInput = defineComponent({
	props: {
		modelValue: { type: [String, Number, Boolean], default: "" },
	},
	setup(props, { attrs, slots }) {
		const showsVariableName = computed(() => {
			return (
				!!props.modelValue &&
				variables.value.some((builderVariable) => builderVariable.variable_name === props.modelValue)
			);
		});
		return () =>
			h(
				Input,
				{
					...attrs,
					modelValue: props.modelValue,
					class: [
						attrs.class,
						showsVariableName.value
							? "[&_input]:font-mono [&_input]:text-sm [&_input]:text-ink-violet-1"
							: "",
					],
				},
				slots,
			);
	},
});

const activeState = ref<string | null>(null);

const updateActiveState = (e: FocusEvent) => {
	const target = e.target as HTMLElement;

	// If focusing popover controls, we preserve the current activeState
	if (target.closest(".background-popover-body")) return;

	const variantRow = target.closest("[data-variant]:not(input)");
	const mainPropRow = target.closest("[data-property]");

	if (variantRow) {
		activeState.value = variantRow.getAttribute("data-variant") as string;
	} else if (mainPropRow) {
		activeState.value = null;
	}
};

const getStyleKey = (prop: string, state: string | null = activeState.value) => {
	return state ? `${state}:${prop}` : prop;
};

const rawBackgroundImage = computed(
	() => (blockController.getStyle(getStyleKey("backgroundImage")) || "") as string,
);
const backgroundColor = computed(() => blockController.getStyle(getStyleKey("backgroundColor")) as any);

const isGradient = computed(() => rawBackgroundImage.value?.includes("gradient"));

const activeTab = ref("color");
watch(
	[activeState, isGradient, rawBackgroundImage],
	() => {
		if (isGradient.value) activeTab.value = "gradient";
		else if (rawBackgroundImage.value) activeTab.value = "image";
		else activeTab.value = "color";
	},
	{ immediate: true },
);

const getDisplayValue = (state: string | null) => {
	const bg = blockController.getStyle(getStyleKey("backgroundImage", state)) as string;
	const color = blockController.getStyle(getStyleKey("backgroundColor", state)) as string;

	if (bg?.includes("gradient")) return "Gradient";
	if (bg) {
		const url = bg.replace(/^url\(['"]?|['"]?\)$/g, "");
		const parts = url.split("/");
		return parts[parts.length - 1] || "Image";
	}
	// show the variable's name instead of its raw value e.g. var(--uuid)
	if (color) return getVariableName(color) ?? color;
	return "";
};

const backgroundImageURL = computed(() => {
	const bgImage = rawBackgroundImage.value;
	return bgImage && !isGradient.value ? bgImage.replace(/^url\(['"]?|['"]?\)$/g, "") : null;
});

const backgroundSize = computed(() => blockController.getStyle(getStyleKey("backgroundSize")) as string);
const backgroundPosition = computed(
	() => blockController.getStyle(getStyleKey("backgroundPosition")) as string,
);
const backgroundRepeat = computed(() => blockController.getStyle(getStyleKey("backgroundRepeat")) as string);
const backgroundClip = computed(
	() =>
		blockController.getStyle(getStyleKey("backgroundClip")) ||
		blockController.getStyle(getStyleKey("WebkitBackgroundClip")),
);
const isTextBlock = computed(() => blockController.isText());

const getHasBackground = (state: string | null) => {
	return Boolean(
		blockController.getStyle(getStyleKey("backgroundImage", state)) ||
			blockController.getStyle(getStyleKey("backgroundColor", state)),
	);
};

const getPreviewStyle = (state: string | null) => {
	const bgValue = blockController.getStyle(getStyleKey("backgroundImage", state)) as string;
	const colorValue = blockController.getStyle(getStyleKey("backgroundColor", state)) as string;
	const size = blockController.getStyle(getStyleKey("backgroundSize", state)) as string;
	const pos = blockController.getStyle(getStyleKey("backgroundPosition", state)) as string;
	const repeat = blockController.getStyle(getStyleKey("backgroundRepeat", state)) as string;

	let bg = "";
	if (bgValue?.includes("gradient")) {
		bg = bgValue;
	} else if (bgValue) {
		const url = bgValue.replace(/^url\(['"]?|['"]?\)$/g, "");
		bg = cssUrl(url);
	}

	return {
		backgroundColor: colorValue ? resolveVariableValue(colorValue, builderStore.canvasDarkMode) : colorValue,
		backgroundImage: bg,
		backgroundPosition: pos,
		backgroundSize: size,
		backgroundRepeat: repeat,
	};
};

const sizeOptions = [
	{ label: "Contain", value: "contain" },
	{ label: "Cover", value: "cover" },
	{ label: "Auto", value: "auto" },
];

const positionOptions = [
	{ label: "Center", value: "center" },
	{ label: "Top", value: "top" },
	{ label: "Bottom", value: "bottom" },
	{ label: "Left", value: "left" },
	{ label: "Right", value: "right" },
];

const repeatOptions = [
	{ label: "No Repeat", value: "no-repeat" },
	{ label: "Repeat", value: "repeat" },
	{ label: "Repeat X", value: "repeat-x" },
	{ label: "Repeat Y", value: "repeat-y" },
];

const setBGImage = (file: { file_url: string }) => {
	blockController.setStyle(getStyleKey("backgroundImage"), cssUrl(file.file_url));
	blockController.setStyle(getStyleKey("backgroundColor"), null);
	if (!blockController.getStyle(getStyleKey("backgroundSize"))) {
		blockController.setStyle(getStyleKey("backgroundSize"), "cover");
	}
	if (!blockController.getStyle(getStyleKey("backgroundPosition"))) {
		blockController.setStyle(getStyleKey("backgroundPosition"), "center");
	}
	if (!blockController.getStyle(getStyleKey("backgroundRepeat"))) {
		blockController.setStyle(getStyleKey("backgroundRepeat"), "no-repeat");
	}
};

const setBGValue = (value: string) => {
	const bgKey = getStyleKey("backgroundImage");
	const colorKey = getStyleKey("backgroundColor");
	const isValidHexValue = (value: string) => /^([0-9A-F]{3}){1,2}$/i.test(value);

	let cleanURL = value;
	if (value?.startsWith("url(")) {
		cleanURL = value.replace(/^url\(['"]?|['"]?\)$/g, "");
	}
	if (isValidHexValue(value)) {
		blockController.setStyle(colorKey, `#${value}`);
		blockController.setStyle(bgKey, null);
	} else if (value?.startsWith("#") || value?.startsWith("rgb") || value?.startsWith("hsl")) {
		blockController.setStyle(colorKey, value);
		blockController.setStyle(bgKey, null);
	} else {
		blockController.setStyle(bgKey, cleanURL ? cssUrl(cleanURL) : null);
		blockController.setStyle(colorKey, null);
	}
};

const setBGColor = (color: string | null) => {
	blockController.setStyle(getStyleKey("backgroundColor"), color);
	if (color) {
		blockController.setStyle(getStyleKey("backgroundImage"), null);
	}
};

const setGradient = (gradient: string) => {
	blockController.setStyle(getStyleKey("backgroundImage"), gradient);
	blockController.setStyle(getStyleKey("backgroundColor"), null);
};

const setBGSize = (value: string) => {
	blockController.setStyle(getStyleKey("backgroundSize"), value);
};

const setBGPosition = (value: string) => {
	blockController.setStyle(getStyleKey("backgroundPosition"), value);
};

const setBGRepeat = (value: string) => {
	blockController.setStyle(getStyleKey("backgroundRepeat"), value);
};

const clearBGImage = () => {
	blockController.setStyle(getStyleKey("backgroundImage"), null);
	blockController.setStyle(getStyleKey("backgroundSize"), null);
	blockController.setStyle(getStyleKey("backgroundPosition"), null);
	blockController.setStyle(getStyleKey("backgroundRepeat"), null);
	blockController.setStyle(getStyleKey("backgroundColor"), null);
};

const setBGClip = (value: boolean) => {
	const clipValue = value ? "text" : null;
	const fillValue = value ? "transparent" : null;

	blockController.setStyle(getStyleKey("backgroundClip"), clipValue);
	blockController.setStyle(getStyleKey("WebkitBackgroundClip"), clipValue);
	blockController.setStyle(getStyleKey("WebkitTextFillColor"), fillValue);
};

const handleSetVariant = (variantName: string, value: string | number | boolean | null) => {
	const bgKey = `${variantName}:backgroundImage`;
	const colorKey = `${variantName}:backgroundColor`;

	if (!value) {
		blockController.setStyle(bgKey, null);
		blockController.setStyle(colorKey, null);
		return;
	}

	// Basic transition logic for states
	blockController.getSelectedBlocks().forEach((block) => {
		if (!block.getStyle("transitionDuration")) {
			block.setStyle("transitionDuration", "300ms");
			block.setStyle("transitionTimingFunction", "ease");
			block.setStyle("transitionProperty", "all");
		}
	});

	// the trigger input is read-only, so a non-null value here can only come from
	// the "copy current value to state" dropdown — copy the actual base styles
	// instead of the display text (e.g. "Gradient", variable name, image file name)
	blockController.setStyle(bgKey, (blockController.getStyle("backgroundImage") as string) ?? null);
	blockController.setStyle(colorKey, (blockController.getStyle("backgroundColor") as string) ?? null);
};

const showServeLocallyButton = computed(() => shouldShowOptimizeButton(backgroundImageURL.value));
const serveLocallyButtonText = computed(() => getOptimizeButtonText(backgroundImageURL.value));

const serveBackgroundImageLocally = () => {
	if (!backgroundImageURL.value) {
		return;
	}

	return optimizeImage({
		imageUrl: backgroundImageURL.value,
		onSuccess: (newUrl: string) => {
			blockController.setStyle(getStyleKey("backgroundImage"), cssUrl(newUrl));
		},
	});
};
</script>
