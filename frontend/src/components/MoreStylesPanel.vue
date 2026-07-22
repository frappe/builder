<template>
	<div class="flex flex-col gap-4">
		<div v-if="propertyRows.length" class="mt-1 flex flex-col gap-4">
			<div
				v-for="row in propertyRows"
				:key="row.property"
				class="flex items-start"
				@contextmenu="showRemoveContextMenu($event, row.property)">
				<StylePropertyControl
					class="max-h-12 min-w-0 flex-1"
					v-bind="row.controlProps"
					:propertyKey="row.styleProperty"
					:label="row.label"
					:getControlAttrs="() => row.controlAttrs" />
			</div>
		</div>
		<ContextMenu ref="contextMenu" :options="contextMenuOptions" />

		<Combobox
			ref="propertyCombobox"
			v-model="selectedProperty"
			:options="propertyOptions"
			placeholder="Add CSS property"
			empty-text="No matching properties"
			open-on-focus
			@update:query="propertySearch = $event"
			@update:modelValue="addProperty">
			<template #suffix="{ open, setOpen }">
				<button
					type="button"
					class="grid size-5 shrink-0 place-items-center rounded text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8"
					aria-label="Add CSS property"
					@click.stop="setOpen(!open)"
					@pointerdown.stop.prevent>
					<span class="lucide-plus size-4" aria-hidden="true" />
				</button>
			</template>
			<template #item-label="{ item }">
				<span class="flex min-w-0 flex-col gap-0.5">
					<span class="truncate text-sm text-ink-gray-8">
						{{ getPropertyLabel(item.value) }}
					</span>
					<code class="truncate font-mono text-xs text-ink-gray-5">
						{{ item.value }}
					</code>
				</span>
			</template>
			<template #item-add-property="{ query }">
				<span class="flex min-w-0 items-center gap-2">
					<span class="min-w-0 truncate text-sm text-ink-gray-8">
						Add
						<code class="font-mono text-xs text-ink-gray-6">{{ query }}</code>
					</span>
				</span>
			</template>
		</Combobox>
	</div>
</template>

<script setup lang="ts">
import ContextMenu from "@/components/ContextMenu.vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import {
	getCSSPropertyControl,
	getCSSPropertyOptions,
	getCSSValueOptions,
	isValidCSSPropertyName,
	type StyleControlConfig,
} from "@/utils/cssMetadata";
import {
	getCuratedStyleProperties,
	getNonCuratedProperties,
	isCuratedStyleProperty,
} from "@/utils/curatedStyleProperties";
import { isInteractiveControl, toStyleProperty } from "@/utils/helpers";
import { Combobox } from "frappe-ui";
import { computed, nextTick, reactive, ref, watch } from "vue";

const STATES = ["hover", "active", "focus"];

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const propertySearch = ref("");
const selectedProperty = ref<string | null>(null);
const contextMenu = ref<InstanceType<typeof ContextMenu> | null>(null);
const contextMenuProperty = ref<string | null>(null);
const propertyCombobox = ref<{ reset: () => void } | null>(null);

// rows added from the picker stay visible until they are removed, even without a value
const addedProperties = reactive(new Set<string>());

const selectedBlock = computed(() => blockController.getFirstSelectedBlock());

watch(
	() => selectedBlock.value?.blockId,
	() => addedProperties.clear(),
);

// styles that apply at the active breakpoint, including the ones it inherits
const cascadingStyles = computed(() => {
	const block = selectedBlock.value;
	if (!block) return {};
	const breakpoint = canvasStore.activeCanvas?.activeBreakpoint;
	if (breakpoint === "mobile") {
		return { ...block.baseStyles, ...block.tabletStyles, ...block.mobileStyles };
	}
	if (breakpoint === "tablet") return { ...block.baseStyles, ...block.tabletStyles };
	return { ...block.baseStyles };
});

const activeProperties = computed(() => {
	const properties = getNonCuratedProperties(cascadingStyles.value);
	addedProperties.forEach((property) => properties.add(property));
	return properties;
});

const getPropertyLabel = (property: string) =>
	property
		.split("-")
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");

// keyword suggestions are only meaningful on the fallback Autocomplete control
const getControlAttrs = (property: string, { component, controlAttrs }: StyleControlConfig) => {
	if (component && component !== Autocomplete) return controlAttrs || {};
	return {
		...controlAttrs,
		getOptions: (query: string) => getCSSValueOptions(property, query),
		showInputAsOption: true,
		allowArbitraryValue: true,
	};
};

const propertyRows = computed(() =>
	Array.from(activeProperties.value)
		.sort()
		.map((property) => {
			const { controlAttrs, options, component, ...controlProps } = getCSSPropertyControl(property);
			return {
				property,
				styleProperty: String(toStyleProperty(property)),
				label: getPropertyLabel(property),
				controlProps: {
					...controlProps,
					component: component || Autocomplete,
					options: options?.length ? options : undefined,
				},
				controlAttrs: getControlAttrs(property, { component, controlAttrs }),
			};
		}),
);

const canAddProperty = (property: string) =>
	isValidCSSPropertyName(property) &&
	!isCuratedStyleProperty(property) &&
	!activeProperties.value.has(property);

const propertyOptions = computed(() => [
	...getCSSPropertyOptions(propertySearch.value, getCuratedStyleProperties()).filter(
		(option) => !activeProperties.value.has(option.value),
	),
	{
		type: "custom" as const,
		key: "add-property",
		label: "Add property",
		slot: "add-property",
		condition: ({ query }: { query: string }) => canAddProperty(query.trim().toLowerCase()),
		onClick: ({ query }: { query: string }) => addProperty(query),
	},
]);

const focusProperty = async (property: string) => {
	await nextTick();
	const selector = `[data-property="${String(toStyleProperty(property))}"]`;
	const row = document.querySelector(selector) as HTMLElement | null;
	row?.scrollIntoView({ block: "nearest" });
	row?.querySelector("input")?.focus();
};

const resetPropertyPicker = (clearPropertyFilter = false) => {
	propertySearch.value = "";
	selectedProperty.value = null;
	if (clearPropertyFilter) builderStore.propertyFilter = null;
	nextTick(() => propertyCombobox.value?.reset());
};

const addProperty = (property: string | null) => {
	const normalizedProperty = property?.trim().toLowerCase();
	if (normalizedProperty && canAddProperty(normalizedProperty)) {
		addedProperties.add(normalizedProperty);
		focusProperty(normalizedProperty);
	}
	resetPropertyPicker();
};

const removeProperty = (property: string) => {
	addedProperties.delete(property);
	blockController.setStyle(toStyleProperty(property), null);
	STATES.forEach((state) => blockController.setStyle(toStyleProperty(`${state}:${property}`), null));
	resetPropertyPicker(true);
};

const contextMenuOptions = [
	{
		label: "Remove",
		action: () => contextMenuProperty.value && removeProperty(contextMenuProperty.value),
	},
];

const showRemoveContextMenu = (event: MouseEvent, property: string) => {
	if (isInteractiveControl(event.target)) return;
	contextMenuProperty.value = property;
	contextMenu.value?.show(event);
};
</script>
