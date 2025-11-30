<template>
	<div ref="propsEditor" class="flex flex-col gap-2">
		<div v-for="(value, key, index) in obj" :key="index" class="flex gap-2">
			<Autocomplete
				:make-fixed="true"
				fix-to=".props-popover-content"
				class="w-full [&>.form-input]:border-none [&>.form-input]:hover:border-none [&>div>input]:text-xs"
				v-bind="events"
				ref="autoCompleteRef"
				placeholder="Prop Name"
				:modelValue="key"
				:getOptions="getAutocompleteOptions"
				@update:modelValue="
					(option) => {
						console.log(option);
						if (typeof option === 'string') {
							return;
						}
						replaceKey(key, option?.value);
					}
				" />
			<Input
				type="select"
				class="!w-16"
				placeholder="operator"
				:modelValue="value.operator"
				@update:modelValue="setSelectedOperator(key, $event)"
				:options="getOperatorOptions(key)"></Input>
			<BuilderInput
				placeholder="Property"
				:modelValue="value.value"
				@update:modelValue="(val: string) => updateObjectValue(key, val)" />
			<BuilderButton
				class="flex-shrink-0 text-xs"
				variant="subtle"
				icon="x"
				@click="deleteObjectKey(key as string)" />
		</div>
		<BuilderButton variant="subtle" label="Add" class="addButton" @click="addObjectKey"></BuilderButton>
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>

<script setup lang="ts">
import { mapToObject, replaceMapKey } from "@/utils/helpers";
import { nextTick, ref, useAttrs, watch } from "vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import blockController from "@/utils/blockController";
import { toast } from "vue-sonner";
import Input from "./Controls/Input.vue";

type DependencyObjType = Record<
	string,
	{
		operator: string;
		value: string;
	}
>;

type availableStdPropsType = Record<string, "string" | "number" | "boolean" | "array" | "object">;

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const propsEditor = ref<HTMLElement | null>(null);
const autoCompleteRef = ref<typeof Autocomplete | null>(null);

const props = defineProps<{
	availableStdProps: availableStdPropsType;
	obj: DependencyObjType;
	description?: string;
}>();

const emit = defineEmits({
	"update:obj": (obj: BlockProps) => true,
});

const setSelectedOperator = (key: string, operator: string) => {
	const map = new Map(Object.entries(props.obj));
	const current = map.get(key);
	if (current) {
		map.set(key, {
			...current,
			operator,
		});
		emit("update:obj", mapToObject(map));
	}
};

const operatorsForString = ["equals", "not equals", "contains", "does not contain"];
const operatorsForNumber = ["equals", "not equals", "greater than", "less than"];
const operatorsForBoolean = ["is true", "is false"];
const operatorsForArray = ["includes", "does not include"];
const operatorsForObject = ["has key", "does not have key"];

const operatorOptionsCache: Record<string, { label: string; value: string }[]> = {};

const getOperatorOptions = (propName: string) => {
	if (!props.availableStdProps[propName]) {
		return [];
	}
	const propType = props.availableStdProps[propName];
	if (operatorOptionsCache[propType]) {
		// to avoid mapping every time
		return operatorOptionsCache[propType];
	}
	let operators: string[] = [];
	switch (propType) {
		case "string":
			operators = operatorsForString;
			break;
		case "number":
			operators = operatorsForNumber;
			break;
		case "boolean":
			operators = operatorsForBoolean;
			break;
		case "array":
			operators = operatorsForArray;
			break;
		case "object":
			operators = operatorsForObject;
			break;
		default:
			operators = [];
	}
	const options = operators.map((op) => ({ label: op, value: op }));
	operatorOptionsCache[propType] = options;
	return options;
};

const getAutocompleteOptions = async (query: string) => {
	const options = Object.entries(props.availableStdProps)
		.filter(([key]) => key.toLowerCase().includes(query.toLowerCase()))
		.map(([key]) => ({
			label: key,
			value: key,
		}));

	return options;
};

const addObjectKey = async () => {
	const map = new Map(Object.entries(props.obj));
	map.set("", { operator: "", value: "" });
	emit("update:obj", mapToObject(map));
	await nextTick();
	const inputs = propsEditor.value?.querySelectorAll("input");
	if (inputs) {
		const lastInput = inputs[inputs.length - 2];
		lastInput.focus();
	}
};

const updateObjectValue = (key: string, value: string | null) => {
	if (!key) {
		toast.error("Please select a property name.");
		return;
	}
	if (!props.obj[key].operator) {
		toast.error("Please select an operator.");
		return;
	}

	const map = new Map(Object.entries(props.obj));

	map.set(key, {
		...map.get(key)!,
		value: value || "",
	});

	emit("update:obj", mapToObject(map));
};

const replaceKey = (oldKey: string, newKey: string) => {
	if (Object.keys(props.obj).includes(newKey)) {
		toast.error("Property name already exists.");
		return;
	}
	if (!newKey) {
		newKey = "";
	}
	const map = new Map(Object.entries(props.obj));
	emit("update:obj", mapToObject(replaceMapKey(map, oldKey, newKey)));
	// need to add the dependdency tracking
};

const deleteObjectKey = (key: string) => {
	const map = new Map(Object.entries(props.obj));
	map.delete(key);
	emit("update:obj", mapToObject(map));
};

watch(
	[() => props.obj, () => props.availableStdProps, () => blockController.getSelectedBlocks()],
	() => {
		if (Array.isArray(autoCompleteRef.value)) {
			autoCompleteRef.value.forEach((ref) => {
				ref?.updateOptions();
			});
		}
	},
	{ immediate: true },
);

const evaluateCondition = (leftOperand: any, operator: string, rightOperand: any, type: string): boolean => {
	try {
		switch (type) {
			case "string":
				const leftStr = String(leftOperand);
				const rightStr = String(rightOperand);
				switch (operator) {
					case "equals":
						return leftStr === rightStr;
					case "not equals":
						return leftStr !== rightStr;
					case "contains":
						return leftStr.includes(rightStr);
					case "does not contain":
						return !leftStr.includes(rightStr);
					default:
						return false;
				}

			case "number":
				const leftNum = Number(leftOperand);
				const rightNum = Number(rightOperand);
				switch (operator) {
					case "equals":
						return leftNum === rightNum;
					case "not equals":
						return leftNum !== rightNum;
					case "greater than":
						return leftNum > rightNum;
					case "less than":
						return leftNum < rightNum;
					default:
						return false;
				}

			case "boolean":
				const boolValue = Boolean(leftOperand);
				switch (operator) {
					case "is true":
						return boolValue === true;
					case "is false":
						return boolValue === false;
					default:
						return false;
				}

			case "array":
				if (!Array.isArray(leftOperand)) return false;
				switch (operator) {
					case "includes":
						return leftOperand.includes(rightOperand);
					case "does not include":
						return !leftOperand.includes(rightOperand);
					default:
						return false;
				}

			case "object":
				if (typeof leftOperand !== "object" || leftOperand === null) return false;
				const key = String(rightOperand);
				switch (operator) {
					case "has key":
						return key in leftOperand;
					case "does not have key":
						return !(key in leftOperand);
					default:
						return false;
				}

			default:
				return false;
		}
	} catch (error) {
		console.error("Error evaluating condition:", error);
		return false;
	}
};
</script>
