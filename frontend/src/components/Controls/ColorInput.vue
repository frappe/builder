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
						<Tooltip :text="isCssVariable ? resolvedColor : null">
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
	</div>
</template>
<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import { StyleToken } from "@/types/Builder/StyleToken";
import { getRGB, toKebabCase } from "@/utils/helpers";
import { useStyleToken } from "@/utils/useStyleToken";
import { Tooltip } from "frappe-ui";
import { computed, ref, useAttrs } from "vue";
import ColorPicker from "./ColorPicker.vue";
import InputLabel from "./InputLabel.vue";

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const colorInput = ref<HTMLInputElement | null>(null);

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
		const { resolveTokenValue } = useStyleToken();
		return resolveTokenValue(props.modelValue);
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

const getOptions = async (query: string) => {
	if (query.startsWith("--") || query.startsWith("var")) {
		let processedQuery = query.replace(/^(--|var|\s+)/, "");
		processedQuery = processedQuery.replace(/^--|\s+/g, "");
		processedQuery = toKebabCase(processedQuery);
		const options = useStyleToken()
			.tokens.value.filter((token: StyleToken) => {
				return token.token_name?.includes(processedQuery);
			})
			.map((token: StyleToken) => {
				return {
					label: `--${toKebabCase(token?.token_name || "")}`,
					value: `var(--${toKebabCase(token?.token_name || "")})`,
				};
			});
		return options;
	} else {
		return [];
	}
};
</script>
