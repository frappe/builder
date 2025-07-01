<template>
	<div class="flex items-center justify-between [&>div>input]:!bg-red-600 [&>div>input]:pr-6">
		<div class="flex w-1/2 min-w-20 max-w-40 items-center justify-between">
			<Dropdown size="sm" :options="stateOptions">
				<template v-slot="{ open }">
					<FeatherIcon
						name="plus-circle"
						class="mr-2 h-3 w-3 cursor-pointer text-ink-gray-7 hover:text-ink-gray-9"
						@click="open" />
				</template>
			</Dropdown>
			<InputLabel v-if="label">{{ label }}</InputLabel>
		</div>
		<BuilderInput
			:type="type"
			:placeholder="placeholder"
			:modelValue="mainValue"
			:options="inputOptions"
			@update:modelValue="onMainChange"
			:hideClearButton="hideClearButton" />
	</div>
	<template v-for="state in statesToShow" :key="String(state)">
		<div
			class="ml-[5px] flex items-center justify-between before:-mt-7 before:h-7 before:w-[1px] before:bg-surface-gray-4 before:content-['_'] after:absolute after:left-3.5 after:h-1.5 after:w-1.5 after:rounded-full after:bg-surface-gray-4 [&>div>input]:!bg-red-600 [&>div>input]:pr-6">
			<InputLabel class="ml-3">{{ stateLabels[String(state)] }}</InputLabel>
			<BuilderInput
				:type="type"
				:placeholder="placeholder"
				:modelValue="getStateValue(String(state))"
				:options="inputOptions"
				@update:modelValue="(v: any) => onStateChange(String(state), v)"
				:hideClearButton="hideClearButton" />
		</div>
	</template>
</template>

<script setup lang="ts">
import { Dropdown, FeatherIcon } from "frappe-ui";
import { computed } from "vue";
import InputLabel from "./InputLabel.vue";

const props = defineProps({
	block: { type: Object, required: true },
	styleProp: { type: String, required: true },
	label: { type: String, default: "" },
	enableStates: { type: Boolean, default: false },
	enabledStates: { type: Array as () => string[], default: () => ["hover", "active"] },
	type: { type: String, default: "text" },
	placeholder: { type: String, default: "unset" },
	options: { type: Array, default: () => [] },
	hideClearButton: { type: Boolean, default: false },
});

const stateLabels: Record<string, string> = {
	hover: "On Hover",
	active: "On Active",
	focus: "On Focus",
};

const inputOptions = computed(() => {
	return (props.options || []).map((option) =>
		typeof option === "object" ? option : { label: option, value: option },
	);
});

const mainValue = computed({
	get() {
		return props.block.getStyle(props.styleProp);
	},
	set(val) {
		props.block.setStyle(props.styleProp, val);
	},
});

function getStateValue(state: string) {
	return props.block.getStyle(`${state}:${props.styleProp}`);
}

function onMainChange(val: any) {
	props.block.setStyle(props.styleProp, val);
}

function onStateChange(state: string, val: any) {
	props.block.setStyle(`${state}:${props.styleProp}`, val);
}

const stateOptions = computed(() =>
	(props.enabledStates as string[])
		.filter((state: string) => !getStateValue(state))
		.map((state: string) => ({
			label: stateLabels[state] || state,
			onClick: () => {
				props.block.setStyle(`${state}:${props.styleProp}`, mainValue.value);
			},
		})),
);

const statesToShow = computed(() => {
	if (!props.enableStates) return [];
	return props.enabledStates.filter((state: string) => {
		return props.block.getStyle(`${state}:${props.styleProp}`) !== undefined;
	});
});
</script>
