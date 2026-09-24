<template>
	<div ref="actionRow" class="relative flex w-full min-w-0 items-center gap-2">
		<span
			v-if="canOpen"
			ref="openAction"
			class="inline-flex shrink-0"
			:class="{ 'absolute invisible': !isActionVisible('open') }">
			<Button variant="solid" size="sm" icon-left="lucide-panel-right" label="Open" @click="emit('open')" />
		</span>

		<span
			ref="toggleAction"
			class="inline-flex shrink-0"
			:class="{ 'absolute invisible': !isActionVisible('toggle') }">
			<Button
				variant="subtle"
				size="sm"
				:icon-left="enabled ? 'lucide-power-off' : 'lucide-power'"
				:label="enabled ? 'Disable' : 'Enable'"
				:loading="working"
				@click="emit('setEnabled', !enabled)" />
		</span>

		<span
			ref="uninstallAction"
			class="inline-flex shrink-0"
			:class="{ 'absolute invisible': !isActionVisible('uninstall') }">
			<Button
				variant="subtle"
				theme="red"
				size="sm"
				icon-left="lucide-trash-2"
				label="Uninstall"
				:loading="working"
				@click="emit('uninstall')" />
		</span>

		<span
			ref="moreAction"
			class="ml-auto inline-flex shrink-0"
			:class="{ 'absolute invisible': !overflowActionIds.length }">
			<Dropdown :options="moreActions" placement="right">
				<template #trigger="{ open }">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-more-horizontal"
						:active="open"
						:disabled="working"
						aria-label="More extension actions" />
				</template>
			</Dropdown>
		</span>
	</div>
</template>

<script setup lang="ts">
import { Button, Dropdown, type DropdownOption, type DropdownOptions } from "frappe-ui";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

type ActionId = "open" | "toggle" | "uninstall";

const props = defineProps<{
	canOpen: boolean;
	enabled: boolean;
	working: boolean;
}>();

const emit = defineEmits<{
	open: [];
	setEnabled: [enabled: boolean];
	uninstall: [];
}>();

const actionRow = ref<HTMLElement | null>(null);
const openAction = ref<HTMLElement | null>(null);
const toggleAction = ref<HTMLElement | null>(null);
const uninstallAction = ref<HTMLElement | null>(null);
const moreAction = ref<HTMLElement | null>(null);
const visibleActionIds = ref<ActionId[]>([]);
let resizeObserver: ResizeObserver | null = null;

const availableActionIds = computed<ActionId[]>(() => [
	...(props.canOpen ? (["open"] as const) : []),
	"toggle",
	"uninstall",
]);

const overflowActionIds = computed(() =>
	availableActionIds.value.filter((action) => !visibleActionIds.value.includes(action)),
);

const actionOptions = computed<Record<ActionId, DropdownOption>>(() => ({
	open: {
		label: "Open",
		icon: "lucide-panel-right",
		onClick: () => emit("open"),
	},
	toggle: {
		label: props.enabled ? "Disable" : "Enable",
		icon: props.enabled ? "lucide-power-off" : "lucide-power",
		onClick: () => emit("setEnabled", !props.enabled),
	},
	uninstall: {
		label: "Uninstall",
		icon: "lucide-trash-2",
		theme: "red",
		onClick: () => emit("uninstall"),
	},
}));

const moreActions = computed<DropdownOptions>(() =>
	overflowActionIds.value.map((action) => actionOptions.value[action]),
);

const isActionVisible = (action: ActionId) => visibleActionIds.value.includes(action);

const fitActions = () => {
	if (!actionRow.value || !moreAction.value) return;

	const elements: Record<ActionId, HTMLElement | null> = {
		open: openAction.value,
		toggle: toggleAction.value,
		uninstall: uninstallAction.value,
	};
	const actions = availableActionIds.value;
	const widths = actions.map((action) => elements[action]?.getBoundingClientRect().width ?? 0);
	if (widths.some((width) => !width)) return;

	const availableWidth = actionRow.value.getBoundingClientRect().width;
	const gap = Number.parseFloat(getComputedStyle(actionRow.value).columnGap) || 0;
	const allActionsWidth = widths.reduce((total, width) => total + width, 0) + gap * (actions.length - 1);

	let visibleCount = actions.length;
	if (allActionsWidth > availableWidth) {
		const moreWidth = moreAction.value.getBoundingClientRect().width;
		visibleCount = getVisibleActionCount(widths, moreWidth, gap, availableWidth);
	}

	const nextVisible = actions.slice(0, visibleCount);
	if (nextVisible.join() !== visibleActionIds.value.join()) visibleActionIds.value = nextVisible;
};

const getVisibleActionCount = (widths: number[], moreWidth: number, gap: number, availableWidth: number) => {
	for (let count = widths.length - 1; count >= 0; count -= 1) {
		const width = widths.slice(0, count).reduce((total, actionWidth) => total + actionWidth, 0);
		if (width + moreWidth + gap * count <= availableWidth) return count;
	}
	return 0;
};

const observeActionRow = async () => {
	await nextTick();
	resizeObserver?.disconnect();
	if (!actionRow.value) return;

	resizeObserver = new ResizeObserver(fitActions);
	[actionRow.value, openAction.value, toggleAction.value, uninstallAction.value, moreAction.value]
		.filter((element): element is HTMLElement => Boolean(element))
		.forEach((element) => resizeObserver?.observe(element));
	fitActions();
};

onMounted(observeActionRow);
onBeforeUnmount(() => resizeObserver?.disconnect());
watch([() => props.canOpen, () => props.enabled], observeActionRow);
</script>
