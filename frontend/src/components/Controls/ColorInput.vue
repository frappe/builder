<template>
	<div>
		<ColorPicker
			ref="colorPickerRef"
			:placement="placement"
			:offset="popoverOffset"
			@open="events.onFocus"
			@close="handleClose"
			:modelValue="resolvedColor"
			@update:modelValue="
				(color) => {
					emit('update:modelValue', color);
				}
			">
			<template #target="{ togglePopover, isOpen }">
				<div class="flex items-center justify-between">
					<InputLabel v-if="label">{{ label }}</InputLabel>
					<div class="relative w-full">
						<Tooltip :text="isCssVariable ? resolvedColor : undefined">
							<Autocomplete
								class="[&>div>input]:pl-8"
								:class="{
									'[&>div>div>input]:text-sm [&>div>div>input]:text-ink-violet-1 [&>div>input]:font-mono':
										isCssVariable,
								}"
								v-bind="events"
								ref="colorInput"
								:referenceElementSelector="autocompleteReferenceElementSelector"
								@keydown.enter="handleEnter"
								@focus="togglePopover"
								:placeholder="placeholder"
								:modelValue="modelValue"
								:getOptions="getOptions"
								:actionButton="
									modelValue && !isCssVariable && props.showColorVariableOptions
										? {
												label: 'Save as Variable',
												icon: 'plus',
												handler: openVariableDialog,
											}
										: undefined
								"
								@update:modelValue="handleColorUpdate">
								<template #prefix>
									<div
										class="size-4 rounded shadow-md"
										@click="togglePopover"
										:style="{
											background: modelValue
												? resolvedColor
												: `url(/assets/builder/images/color-circle.png) center / contain`,
										}"></div>
								</template>
							</Autocomplete>
						</Tooltip>
					</div>
				</div>
			</template>
		</ColorPicker>
		<NewBuilderVariable v-model="showVariableDialog" :variable="newVariable" @success="handleVariableSaved" />
	</div>
</template>
<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import NewBuilderVariable from "@/components/Modals/NewBuilderVariable.vue";
import { BuilderVariable } from "@/types/Builder/BuilderVariable";
import { getRGB, toKebabCase } from "@/utils/helpers";
import { useBuilderVariable } from "@/utils/useBuilderVariable";
import { useDark } from "@vueuse/core";
import { Tooltip } from "frappe-ui";
import {
	computed,
	ComputedRef,
	defineComponent,
	h,
	nextTick,
	onMounted,
	ref,
	shallowRef,
	useAttrs,
	watch,
} from "vue";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

const isDark = useDark({
	attribute: "data-theme",
});

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const colorInput = ref<typeof Autocomplete | null>(null);
const colorPickerRef = ref<typeof ColorPicker | null>(null);
const showVariableDialog = ref(false);
const newVariable = ref<Partial<BuilderVariable> | null>(null);
const { variables, resolveVariableValue } = useBuilderVariable();

const handleEnter = () => {
	const val = props.modelValue;

	// if current value is invalid, clear it
	if (typeof val === "string" && !isValidColorInput(val)) {
		emit("update:modelValue", null);
	}
};

const handleColorUpdate = (val: string | null) => {
	//auto strip extra hashes
	if (typeof val == "string") {
		val = normalizeColorInput(val);
	}

	//last valid value is retained
	const isInvalid = !!val && !isValidColorInput(val);
	if (isInvalid) {
		const lastValidValue = props.modelValue;
		// step 1: clear input
		emit("update:modelValue", null);

		// step 2: restore last valid value after render
		nextTick(() => {
			emit("update:modelValue", lastValidValue ?? null);
		});

		return;
	}

	if (typeof val === "string" && (val.startsWith("var(--") || val.startsWith("--"))) {
		emit("update:modelValue", val.startsWith("var(--") ? val : `var(${val})`);
	} else {
		const color = getRGB(val);
		emit("update:modelValue", color);
	}
};

const normalizeColorInput = (val: string) => {
	// turn multiple leading hashes into one
	if (/^#+/.test(val)) {
		return "#" + val.replace(/^#+/, "");
	}
	return val;
};

const isValidColorInput = (val: string | null) => {
	if (!val) return true;

	// rgb / rgba
	if (/^rgba?\(/.test(val)) return true;

	// hex: #RGB or #RRGGBB
	if (/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(val)) return true;

	// CSS variable
	if (val.startsWith("var(--") || val.startsWith("--")) return true;

	return false;
};

const props = withDefaults(
	defineProps<{
		modelValue?: HashString | null;
		label?: string;
		placeholder?: string;
		placement?: "top" | "bottom" | "left" | "right";
		showColorVariableOptions?: boolean;
		showPickerOnMount?: boolean;
		popoverOffset?: number;
		autocompleteReferenceElementSelector?: string;
	}>(),
	{
		modelValue: null,
		placeholder: "Set Color",
		placement: "left",
		showColorVariableOptions: true,
		showPickerOnMount: false,
	},
);
const lastValidValue = ref<string | null>(props.modelValue ?? null);

watch(
	() => props.modelValue,
	(val) => {
		// keep track of the last valid value so we can restore it when user types invalid input
		if (isValidColorInput(val as string | null)) {
			lastValidValue.value = (val as string) ?? null;
		}
	},
);

const isCssVariable = computed(() => {
	return (
		typeof props.modelValue === "string" &&
		(props.modelValue.startsWith("var(--") || props.modelValue.startsWith("--"))
	);
});

const resolvedColor = computed(() => {
	if (!props.modelValue) return "";
	if (isCssVariable.value) {
		return resolveVariableValue(props.modelValue, isDark.value);
	}
	return props.modelValue;
}) as ComputedRef<HashString | RGBString>;

const emit = defineEmits(["update:modelValue"]);

const handleClose = () => {
	if (colorInput.value && typeof colorInput.value.blur === "function") {
		colorInput.value.blur();
	}
	if (typeof events.onBlur === "function") {
		events.onBlur();
	}
};

const openVariableDialog = () => {
	newVariable.value = {
		value: props.modelValue || "",
	};
	showVariableDialog.value = true;
};

const handleVariableSaved = (savedVariable: BuilderVariable) => {
	emit("update:modelValue", `var(--${toKebabCase(savedVariable.variable_name || "")})`);
};

const getOptions = async (query: string) => {
	if (!props.showColorVariableOptions) {
		return [];
	}

	let processedQuery = query.replace(/^(--|var|\s+)/, "");
	processedQuery = processedQuery.replace(/^--|\(|\s+/g, "");
	const options = variables.value
		.filter((builderVariable: BuilderVariable) => {
			const name = (builderVariable.variable_name || "").toLowerCase();
			const queryLower = processedQuery.toLowerCase();
			return queryLower === "" || name.includes(queryLower);
		})
		.map((builderVariable: BuilderVariable) => {
			const varName = `var(--${toKebabCase(builderVariable?.variable_name || "")})`;
			const resolvedLightColor = resolveVariableValue(varName);
			const resolvedDarkColor = resolveVariableValue(varName, true);
			return {
				label: `${builderVariable?.variable_name || ""}`,
				value: varName,
				prefix: shallowRef(
					defineComponent({
						setup() {
							return () =>
								h("div", {
									class: "h-4 w-4 rounded shadow-sm border border-outline-gray-1 flex-shrink-0",
									style: { background: isDark.value ? resolvedDarkColor : resolvedLightColor },
								});
						},
					}),
				),
				// edit
				suffix: !builderVariable.is_standard
					? shallowRef(
							defineComponent({
								setup() {
									const openEdit = () => {
										newVariable.value = { ...builderVariable };
										showVariableDialog.value = true;
									};
									return () =>
										h(
											"Button",
											{
												class: "hidden group-hover:inline-block",
												onClick: (e: Event) => {
													colorPickerRef.value?.togglePopover(false);
													openEdit();
												},
											},
											"Edit",
										);
								},
							}),
						)
					: undefined,
			};
		});
	return options;
};

watch(variables, () => {
	colorInput.value?.refreshOptions();
});
onMounted(() => {
	if (
		props.showPickerOnMount &&
		colorPickerRef.value &&
		typeof colorPickerRef.value.togglePopover === "function"
	) {
		colorPickerRef.value.togglePopover();
	}
});
</script>
