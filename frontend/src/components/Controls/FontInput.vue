<template>
	<div class="relative w-full">
		<Tooltip :text="isCssVariable ? resolvedFont : undefined">
			<Autocomplete
				ref="fontInput"
				:class="{
					'[&>div>div>input]:text-ink-violet-6 [&>div>input]:font-mono': isCssVariable,
				}"
				:modelValue="modelValue"
				:displayValue="displayValue"
				:placeholder="displayPlaceholder"
				:getOptions="getOptions"
				:actionButton="{ component: FontUploader }"
				:inputStyle="inputStyle"
				@update:modelValue="handleUpdate" />
		</Tooltip>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import FontUploader from "@/components/Controls/FontUploader.vue";
import userFonts from "@/data/userFonts";
import { BuilderToken, UserFont } from "@/types/doctypes";
import { filterOptions } from "@/utils/autocompleteOptions";
import { enqueuePreviewLoad, fontListItems, loadFontList, previewFontStyle } from "@/utils/fontManager";
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
	},
);

const emit = defineEmits(["update:modelValue"]);

type FontOption = {
	label: string;
	value: string;
	labelStyle?: () => { fontFamily: string } | undefined;
	previewFont?: string;
};

const { fontTokens, resolveVariableValue, getVariableName } = useBuilderToken();
const fontInput = ref<typeof Autocomplete | null>(null);

const isToken = (value?: string | null): value is string =>
	typeof value === "string" && (value.startsWith("var(--") || value.startsWith("--"));

const isCssVariable = computed(() => isToken(props.modelValue));

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
	if (!p) return __("Set Font");
	return isToken(p) ? getVariableName(p) ?? p : p;
});

// the field doubles as a specimen: whatever family name it shows — the one that is set,
// or the inherited one standing in as placeholder — is rendered in that family. Both are
// already applied on the canvas, so the face is loaded. A token shows its own name rather
// than a family, so it keeps the mono treatment that marks it as one.
const inputStyle = computed(() => {
	const family = props.modelValue || props.placeholder;
	if (!family || isToken(family)) return undefined;
	return { fontFamily: family };
});

const handleUpdate = (val: string | null) => emit("update:modelValue", val);

const getOptions = async (filterString: string) => {
	await loadFontList();
	// each row renders in its own typeface; previewFontStyle stays undefined until that
	// face is usable, so labels never flash a fallback
	const toOption = (family: string) => ({
		label: family,
		value: family,
		labelStyle: () => previewFontStyle(family),
		previewFont: family,
	});
	// a token's name is what the field shows when one is picked, and it matches no
	// family: filtering the font lists by it would leave only the token to choose from
	const fontQuery = isCssVariable.value && filterString === displayValue.value ? "" : filterString;

	// Font design tokens first: picking one stores var(--id), so retheming the
	// token updates every block bound to it. The family is part of the label, so
	// it stays searchable.
	const tokenOptions = filterOptions(
		fontTokens.value.map((token: BuilderToken) => {
			const label = `${token.token_name || token.value} (${token.value})`;
			// previewed against the whole label, since it carries the token's name as well
			// as the family, and a subset cut to the family alone could not render it
			return {
				label,
				value: `var(--${token.name})`,
				labelStyle: () => previewFontStyle(label),
				previewFont: token.value as string,
			};
		}),
		filterString,
	);
	const userFontOptions = filterOptions(
		(userFonts.data || []).map((font: UserFont) => toOption(font.font_name as string)),
		fontQuery,
	);
	const defaultFontOptions = filterOptions(
		fontListItems.value.map((font) => toOption(font.family)),
		fontQuery,
	);

	const options: FontOption[] = [];
	if (tokenOptions.length) {
		options.push({ label: __("Design tokens"), value: "_separator_0" }, ...tokenOptions);
	}
	if (userFontOptions.length) {
		options.push({ label: __("Custom"), value: "_separator_1" }, ...userFontOptions);
	}
	if (defaultFontOptions.length) {
		// the heading only earns its place once something sits under it
		if (options.length) options.push({ label: __("Default"), value: "_separator_2" });
		options.push(...defaultFontOptions);
	}

	// separators are the only entries without a preview
	enqueuePreviewLoad(
		options.flatMap((o) => (o.previewFont ? [{ font: o.previewFont, label: o.label }] : [])),
	);
	return options;
};

// a newly-saved Font token should appear in the list without reopening the panel
watch(fontTokens, () => fontInput.value?.refreshOptions());
</script>
