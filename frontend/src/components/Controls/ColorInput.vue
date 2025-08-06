<template>
	<div>
		<ColorPicker
			:placement="placement"
			@open="events.onFocus"
			@close="handleClose"
			:modelValue="modelValue"
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
									'[&>div>input]:font-mono [&>div>input]:text-xs [&>div>input]:text-ink-violet-1':
										isCssVariable,
								}"
								v-bind="events"
								ref="colorInput"
								@focus="togglePopover"
								:placeholder="placeholder"
								:modelValue="modelValue"
								:getOptions="getOptions"
								:actionButton="
									modelValue && !isCssVariable
										? {
												label: 'Save as Variable',
												icon: 'plus',
												handler: openVariableDialog,
											}
										: undefined
								"
								@update:modelValue="
									(val) => {
										// if value is object, extract the value
										if (typeof val === 'object' && val !== null) {
											val = val.value;
										}
										// If it's a CSS variable, preserve it
										if (typeof val === 'string' && (val.startsWith('var(--') || val.startsWith('--'))) {
											emit('update:modelValue', val.startsWith('var(--') ? val : `var(${val})`);
										} else {
											// For direct color values, convert to RGB
											const color = getRGB(val);
											emit('update:modelValue', color);
										}
									}
								">
								<template #prefix>
									<div
										class="h-4 w-4 rounded shadow-sm"
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
import { Tooltip } from "frappe-ui";
import { computed, ref, useAttrs, watch } from "vue";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const colorInput = ref<typeof Autocomplete | null>(null);
const showVariableDialog = ref(false);
const newVariable = ref<Partial<BuilderVariable> | null>(null);
const { variables, resolveVariableValue } = useBuilderVariable();

const props = withDefaults(
	defineProps<{
		modelValue?: HashString | null;
		label?: string;
		placeholder?: string;
		placement?: string;
	}>(),
	{
		modelValue: null,
		placeholder: "Set Color",
		placement: "left",
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
		return resolveVariableValue(props.modelValue);
	}
	return props.modelValue;
});

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
	let processedQuery = query.replace(/^(--|var|\s+)/, "");
	processedQuery = processedQuery.replace(/^--|\(|\s+/g, "");
	processedQuery = toKebabCase(processedQuery);
	const options = variables.value
		.filter((builderVariable: BuilderVariable) => {
			return builderVariable.variable_name?.includes(processedQuery);
		})
		.map((builderVariable: BuilderVariable) => {
			return {
				label: `${builderVariable?.variable_name || ""}`,
				value: `var(--${toKebabCase(builderVariable?.variable_name || "")})`,
			};
		})
		.slice(0, 8);
	return options;
};

watch(variables, () => {
	colorInput.value?.updateOptions();
});
</script>
