<template>
	<div class="relative w-full">
		<Tooltip :text="isCssVariable ? resolvedFont : undefined">
			<Autocomplete
				ref="fontInput"
				class="[&>div>input]:pl-9"
				:class="{
					'[&>div>div>input]:text-ink-violet-6 [&>div>input]:font-mono': isCssVariable,
				}"
				:modelValue="displayValue"
				:placeholder="displayPlaceholder"
				:getOptions="getOptions"
				:actionButton="{ component: FontInputActions }"
				@update:modelValue="handleUpdate">
				<template #prefix>
					<div
						class="flex size-4 items-center justify-center rounded bg-surface-gray-3 text-xs leading-none text-ink-gray-7 shadow-sm"
						:style="{ fontFamily: resolvedFont }">
						A
					</div>
				</template>
			</Autocomplete>
		</Tooltip>
	</div>
</template>

<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import FontInputActions from "@/components/Controls/FontInputActions.vue";
import userFonts from "@/data/userFonts";
import { UserFont } from "@/types/doctypes";
import { fontList } from "@/utils/fontManager";
import { useBuilderToken } from "@/utils/useBuilderToken";
import { Tooltip } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue?: string | null;
		placeholder?: string;
	}>(),
	{
		modelValue: null,
		placeholder: "Set Font",
	},
);

const emit = defineEmits(["update:modelValue"]);

const { fontTokens, resolveVariableValue, getVariableName } = useBuilderToken();
const fontInput = ref<typeof Autocomplete | null>(null);

const isCssVariable = computed(
	() =>
		typeof props.modelValue === "string" &&
		(props.modelValue.startsWith("var(--") || props.modelValue.startsWith("--")),
);

// resolve a Font token to its real family so the specimen renders in it
const resolvedFont = computed(() => {
	if (!props.modelValue) return "inherit";
	return isCssVariable.value ? resolveVariableValue(props.modelValue) : props.modelValue;
});

// show the token's friendly name instead of the raw var(--uuid), mirroring the color field
const displayValue = computed(() => {
	if (props.modelValue && isCssVariable.value) {
		return getVariableName(props.modelValue) ?? props.modelValue;
	}
	return props.modelValue;
});

// a cascading/inherited placeholder may itself be a token — show its name, not var(--uuid)
const displayPlaceholder = computed(() => {
	const p = props.placeholder;
	if (typeof p === "string" && (p.startsWith("var(--") || p.startsWith("--"))) {
		return getVariableName(p) ?? p;
	}
	return p;
});

const handleUpdate = (val: string | null) => emit("update:modelValue", val);

const getOptions = async (filterString: string) => {
	const query = (filterString || "").toLowerCase();
	const options = [] as { label: string; value: string }[];

	// Font design tokens first: picking one stores var(--id), so retheming the
	// token updates every block bound to it.
	const matchingTokens = fontTokens.value.filter(
		(t: any) =>
			!query ||
			(t.token_name || t.value).toLowerCase().includes(query) ||
			t.value.toLowerCase().includes(query),
	);
	if (matchingTokens.length) {
		options.push({ label: "Design tokens", value: "_separator_0" });
		matchingTokens.forEach((t: any) =>
			options.push({ label: `${t.token_name || t.value} (${t.value})`, value: `var(--${t.name})` }),
		);
	}

	const customStart = options.length;
	userFonts.data.forEach((font: UserFont) => {
		if (options.length >= 20) return;
		const fontName = font.font_name as string;
		if (!query || fontName.toLowerCase().includes(query)) {
			options.push({ label: fontName, value: fontName });
		}
	});
	if (options.length > customStart) {
		options.splice(customStart, 0, { label: "Custom", value: "_separator_1" });
	}

	if (options.length) {
		options.push({ label: "Default", value: "_separator_2" });
	}
	fontList.items.forEach((font) => {
		if (options.length >= 20) return;
		if (!query || font.family.toLowerCase().includes(query)) {
			options.push({ label: font.family, value: font.family });
		}
	});
	return options;
};

// a newly-saved Font token should appear in the list without reopening the panel
watch(fontTokens, () => fontInput.value?.refreshOptions());
</script>
