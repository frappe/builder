<template>
	<div ref="propsEditor" class="flex flex-col gap-2">
		<div v-for="(value, key, index) in obj" :key="index" class="flex gap-2">
			<BuilderInput
				placeholder="Property"
				:modelValue="key"
				:disabled="value.usedByCount || false"
				@update:modelValue="(val: string) => replaceKey(key, val)" />
			<Autocomplete
				class="w-full [&>.form-input]:border-none [&>.form-input]:hover:border-none [&>div>input]:font-mono [&>div>input]:text-xs"
				:class="{
					'[&>div>input]:pl-8': value.value,
					'[&>div>input]:text-ink-gray-7': !value.value,
					'[&>.form-input]:bg-surface-violet-1 [&>div>input]:text-ink-violet-1':
						value.type == 'dynamic' && value.value,
					'[&>.form-input]:bg-surface-blue-1 [&>div>input]:text-ink-blue-3':
						value.type == 'static' && value.value,
					'[&>.form-input]:bg-surface-green-1 [&>div>input]:text-ink-green-3':
						value.type == 'inherited' && value.value && listOfAvailablePropsToInherit.includes(value.value),
					'[&>.form-input]:bg-surface-red-1 [&>div>input]:text-ink-red-3':
						value.type == 'inherited' && value.value && !listOfAvailablePropsToInherit.includes(value.value),
				}"
				v-bind="events"
				ref="autoCompleteRef"
				placeholder="undefined"
				:modelValue="value.value"
				:getOptions="getOptions"
				@update:modelValue="
					(option) => {
						updateObjectValue(key, typeof option == 'string' ? option : option?.value);
					}
				">
				<template #prefix v-if="value.value">
					<LucideZap v-if="value.type == 'dynamic'" class="absolute left-0 top-0 h-4 w-4 text-ink-violet-1" />
					<LucideCaseSensitive
						v-else-if="value.type == 'static'"
						class="absolute left-0 top-0 h-4 w-4 text-ink-blue-3" />
					<LucideListTree
						v-else-if="value.type == 'inherited'"
						class="absolute left-0 top-0 h-4 w-4"
						:class="{
							'text-ink-green-3': listOfAvailablePropsToInherit.includes(value.value),
							'text-ink-red-3': !listOfAvailablePropsToInherit.includes(value.value),
						}" />
				</template>
			</Autocomplete>
			<BuilderButton
				class="flex-shrink-0 text-xs"
				variant="subtle"
				icon="x"
				:disabled="value.usedByCount || false"
				@click="deleteObjectKey(key as string)" />
		</div>
		<Popover popoverClass="!mr-[20px]" placement="left">
			<template #target="{ togglePopover }">
				<BuilderButton class="w-full" variant="subtle" label="Add" @click="togglePopover()"></BuilderButton>
			</template>
			<template #body>
				<PropsPopoverContent />
			</template>
		</Popover>
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import { getCollectionKeys, getDataForKey, mapToObject, replaceMapKey } from "@/utils/helpers";
import { computed, defineComponent, h, nextTick, ref, shallowRef, useAttrs, watch, watchEffect } from "vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { toast } from "vue-sonner";

import Block from "@/block";
// @ts-ignore
import LucideZap from "~icons/lucide/zap";
// @ts-ignore
import LucideCaseSensitive from "~icons/lucide/case-sensitive";
// @ts-ignore
import LucideListTree from "~icons/lucide/list-tree";
import { Popover } from "frappe-ui";
import PropsPopoverContent from "./PropsPopoverContent.vue";

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const autoCompleteRef = ref<typeof Autocomplete | null>(null);

const pageStore = usePageStore();

const props = defineProps<{
	obj: BlockProps;
	description?: string;
}>();

const propsEditor = ref<HTMLElement | null>(null);

const emit = defineEmits({
	"update:obj": (obj: BlockProps) => true,
	"update:ancestorUpdateDependency": (propKey: string, action: "add" | "remove") => true,
});
// better name
type PropOptions = { path: string; type: "dynamic" | "inherited" | "static" };

// why computed? no dependency tracking needed right?
const dataArray = computed(() => {
	const result: PropOptions[] = [];
	let collectionObject = pageStore.pageData;
	if (blockController.getFirstSelectedBlock()?.isInsideRepeater()) {
		const keys = getCollectionKeys(blockController.getFirstSelectedBlock());
		collectionObject = keys.reduce((acc: any, key: string) => {
			const data = getDataForKey(acc, key);
			return Array.isArray(data) && data.length > 0 ? data[0] : data;
		}, collectionObject);
	}

	function processObject(obj: Record<string, any>, prefix = "") {
		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (typeof value === "object" && value !== null && !Array.isArray(value)) {
				processObject(value, path);
			} else if (["string", "number", "boolean"].includes(typeof value)) {
				result.push({ path, type: "dynamic" });
			}
		});
	}

	processObject(collectionObject);
	return result;
});

const listOfAvailablePropsToInherit = ref<string[]>([]);
const getParentProps = (baseBlock: Block, baseProps: PropOptions[]): PropOptions[] => {
	const parentBlock = baseBlock.getParentBlock();
	if (parentBlock) {
		const parentProps: PropOptions[] = Object.keys(parentBlock.getBlockProps()).map((key) => ({
			path: key,
			type: "inherited",
		}));
		const combinedProps = [...baseProps, ...parentProps].reduce((acc, prop) => {
			if (
				!acc.find((p: PropOptions) => p.path === prop.path && p.type === prop.type && p.type === "inherited")
			) {
				acc.push(prop);
			}
			return acc;
		}, [] as PropOptions[]);
		return getParentProps(parentBlock, combinedProps);
	} else {
		return baseProps;
	}
};

const getOptions = async (query: string) => {
	const parentPropsArray = getParentProps(blockController.getFirstSelectedBlock()!, []);

	const options = [
		...new Set([...parentPropsArray, ...dataArray.value]),
		...(query ? [{ path: query, type: "static" } as PropOptions] : []),
	]
		.filter((prop) => prop.path.toLowerCase().includes(query.toLowerCase()))
		.map((prop) => ({
			label: prop.path || "",
			value: `${prop.type}--${prop.path}`,
			suffix: h(
				prop.type === "dynamic" ? LucideZap : prop.type === "static" ? LucideCaseSensitive : LucideListTree,
				{
					class: "ml-2 rounded px-1 py-0.5 text-xs text-ink-gray-6 shrink-0",
				},
			),
		}));

	return options;
};

const addObjectKey = async () => {
	const map = new Map(Object.entries(props.obj));
	map.set("", { type: "static", value: "" });
	emit("update:obj", mapToObject(map));
	await nextTick();
	const inputs = propsEditor.value?.querySelectorAll("input");
	if (inputs) {
		const lastInput = inputs[inputs.length - 2];
		lastInput.focus();
	}
};

const clearObjectValue = (key: string) => {
	const map = new Map(Object.entries(props.obj));
	const oldValue = map.get(key);

	map.set(key, {
		...oldValue!,
		value: null,
		type: "static",
	});

	emit("update:obj", mapToObject(map));

	if (oldValue?.type == "inherited" && oldValue?.value) {
		emit("update:ancestorUpdateDependency", oldValue.value, "remove");
	}
};

const updateObjectValue = (key: string, value: string | null) => {
	if (!key) {
		toast.error("Property name cannot be empty.");
		return;
	}
	if (!value) {
		clearObjectValue(key);
		return;
	}

	const map = new Map(Object.entries(props.obj));
	const splitValue = value.split("--");
	let type, path;
	if (splitValue.length >= 2 && ["dynamic", "inherited", "static"].includes(splitValue[0])) {
		type = splitValue[0];
		path = splitValue.slice(1).join("--");
	} else {
		type = "static";
		path = value;
	}
	const oldPath = map.get(key)?.value;

	map.set(key, {
		...map.get(key)!,
		value: type === "static" ? JSON.stringify(path) : path,
		type: type as BlockProps[string]["type"],
	});

	emit("update:obj", mapToObject(map));

	if (path) {
		emit("update:ancestorUpdateDependency", path, "add");
	} else if (oldPath) {
		emit("update:ancestorUpdateDependency", oldPath, "remove");
	}
};

const replaceKey = (oldKey: string, newKey: string) => {
	const map = new Map(Object.entries(props.obj));
	emit("update:obj", mapToObject(replaceMapKey(map, oldKey, newKey)));
};

const deleteObjectKey = (key: string) => {
	const map = new Map(Object.entries(props.obj));
	const value = map.get(key);
	const path = value?.value;
	map.delete(key);
	emit("update:obj", mapToObject(map));
	if (path) emit("update:ancestorUpdateDependency", path, "remove");
};

watch(
	[() => props.obj, () => blockController.getSelectedBlocks(), () => pageStore.pageData],
	() => {
		if (Array.isArray(autoCompleteRef.value)) {
			autoCompleteRef.value.forEach((ref) => {
				ref?.updateOptions();
			});
		}
		listOfAvailablePropsToInherit.value = getParentProps(blockController.getFirstSelectedBlock()!, []).map(
			(prop) => prop.path,
		);
	},
	{ immediate: true },
);
</script>
