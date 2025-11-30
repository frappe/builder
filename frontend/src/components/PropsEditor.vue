<template>
	<div ref="propsEditor" class="flex flex-col gap-2">
		<div class="flex flex-col gap-2 rounded-lg">
			<template v-for="(value, key, index) in sortedObj" :key="index">
				<div
					:key="index"
					class="prop-list-item relative flex w-full flex-col rounded-sm bg-surface-gray-2 p-2"
					v-if="value.isStandard !== true || shouldDisplayStandardProps">
					<Popover popoverClass="!mr-[25px]" placement="left-start">
						<template #target="{ open }">
							<div class="flex w-full items-center justify-between">
								<div class="flex w-fit max-w-[60%] items-center gap-2 pl-2">
									<div class="icon">
										<component
											v-if="!value.isStandard"
											:is="
												{
													static: LucideCaseSensitive,
													inherited: LucideListTree,
													dynamic: LucideZap,
												}[value.type] || LucideZap
											"
											class="h-4 w-4 text-ink-gray-6" />
										<component
											v-if="value.isStandard && value.standardOptions?.type"
											:is="
												{
													number: LucideNumber,
													string: LucideString,
													boolean: LucideBoolean,
													select: LucideSelect,
													object: LucideObject,
													array: LucideArray,
												}[value.standardOptions?.type] || LucideZap
											"
											class="h-4 w-4 text-ink-gray-6" />
									</div>
									<div class="flex max-w-full flex-col gap-1">
										<p class="text-sm font-medium text-ink-gray-8">
											{{ key }}
										</p>
										<p v-if="value.isStandard" class="text-xs text-ink-gray-6">
											Std. - {{ value.standardOptions?.isRequired ? "Required" : "Optional" }}
										</p>
										<p v-else class="max-w-full truncate text-ellipsis text-xs text-ink-gray-6">
											{{ value.value }}
										</p>
									</div>
								</div>
								<div class="flex-shrink-0 gap-1 rounded">
									<BuilderButton
										class="flex-shrink-0 bg-transparent text-xs"
										variant="subtle"
										icon="edit-2"
										@click.stop="
											() => {
												popupMode = 'edit';
												popoverContentItemsRef[index]?.reset({
													keepName: false,
													keepIsStandard: false,
													keepProps: true,
													keepType: false,
												});
												keyBeingEdited = key as string;
												open();
											}
										" />
									<BuilderButton
										class="flex-shrink-0 bg-transparent text-xs"
										variant="subtle"
										icon="x"
										@click="deleteObjectKey(key as string)" />
								</div>
							</div>
						</template>
						<template #body>
							<PropsPopoverContent
								ref="popoverContentItemsRef"
								mode="edit"
								:propName="key as string"
								:propDetails="value"
								@update:prop="updateProp" />
						</template>
					</Popover>
				</div>
			</template>
		</div>
		<Popover ref="popOverRef" popoverClass="!mr-[20px]" placement="left">
			<template #target="{ open }">
				<BuilderButton
					class="w-full"
					variant="subtle"
					label="Add"
					@click="
						() => {
							popoverContentAddRef?.reset({
								keepName: false,
								keepIsStandard: false,
								keepProps: false,
								keepType: false,
							});
							keyBeingEdited = null;
							popupMode = 'add';
							open();
						}
					"></BuilderButton>
			</template>
			<template #body>
				<PropsPopoverContent
					ref="popoverContentAddRef"
					:mode="popupMode"
					:propName="keyBeingEdited"
					:propDetails="propDetailsOfKeyBeingEdited"
					@add:prop="addProp"
					@update:prop="updateProp" />
			</template>
		</Popover>
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import { mapToObject, replaceMapKey } from "@/utils/helpers";
import { computed, ref, useAttrs, watch } from "vue";

import { toast } from "vue-sonner";

// @ts-ignore
import LucideZap from "~icons/lucide/zap";
// @ts-ignore
import LucideCaseSensitive from "~icons/lucide/case-sensitive";
// @ts-ignore
import LucideListTree from "~icons/lucide/list-tree";
// @ts-ignore
import LucideNumber from "~icons/lucide/pi";
// @ts-ignore
import LucideString from "~icons/lucide/type";
// @ts-ignore
import LucideBoolean from "~icons/lucide/toggle-right";
// @ts-ignore
import LucideSelect from "~icons/lucide/chevrons-up-down";
// @ts-ignore
import LucideArray from "~icons/lucide/brackets";
// @ts-ignore
import LucideObject from "~icons/lucide/braces";

import { Popover } from "frappe-ui";
import PropsPopoverContent from "./PropsPopoverContent.vue";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";

const attrs = useAttrs();
const events = Object.fromEntries(
	Object.entries(attrs).filter(([key]) => key.startsWith("onFocus") || key.startsWith("onBlur")),
);

const popupMode = ref<"add" | "edit">("add");
const keyBeingEdited = ref<string | null>(null);
const propDetailsOfKeyBeingEdited = ref<BlockProps[string] | null>(null);
const popOverRef = ref<typeof Popover | null>(null);
const popoverContentAddRef = ref<typeof PropsPopoverContent | null>(null);
const popoverContentItemsRef = ref<Array<typeof PropsPopoverContent | null>>([]);

const props = defineProps<{
	obj: BlockProps;
	description?: string;
}>();

const sortedObj = computed(() => {
	// Sort props: standard props at the front, then non-standard props
	const entries = Object.entries(props.obj || {});
	entries.sort((a, b) => {
		const aIsStandard = a[1].isStandard ? 1 : 0;
		const bIsStandard = b[1].isStandard ? 1 : 0;
		return bIsStandard - aIsStandard;
	});
	return Object.fromEntries(entries);
});

const shouldDisplayStandardProps = computed(() => {
	return (
		useCanvasStore().editingMode == "fragment" && !blockController.getFirstSelectedBlock()?.getParentBlock()
	);
});

const propsEditor = ref<HTMLElement | null>(null);

const emit = defineEmits({
	"update:obj": (obj: BlockProps) => true,
});

const addProp = async (name: string, value: BlockProps[string]) => {
	const map = new Map(Object.entries(props.obj));
	map.set(name, value);
	popupMode.value = "edit";
	keyBeingEdited.value = name;
	emit("update:obj", mapToObject(map));
	return map;
};

const clearObjectValue = (map: Map<string, BlockProps[string]>, key: string) => {
	const oldValue = map.get(key);

	map.set(key, {
		...oldValue!,
		value: null,
		type: "static",
	});

	return map;
};

const updateObjectValue = (
	map: Map<string, BlockProps[string]>,
	key: string,
	{ value, type }: { value: string | null; type: string },
) => {
	const path = value;
	if (!path) {
		return clearObjectValue(map, key);
	}

	const oldPath = map.get(key)?.value;
	const oldType = map.get(key)?.type;

	if (path === oldPath && type === oldType) {
		return map;
	}

	map.set(key, {
		...map.get(key)!,
		value: type === "static" && typeof path !== "string" ? JSON.stringify(path) : path,
		type: type as BlockProps[string]["type"],
	});

	return map;
};

const replaceKey = (map: Map<string, BlockProps[string]>, oldKey: string, newKey: string) => {
	keyBeingEdited.value = newKey;
	return mapToObject(replaceMapKey(map, oldKey, newKey));
};

const updateIsStandard = (map: Map<string, BlockProps[string]>, key: string, isStandard: boolean) => {
	const value = map.get(key);
	map.set(key, {
		...value!,
		isStandard,
	});
	return map;
};

const updateStandardOptions = (map: Map<string, BlockProps[string]>, key: string, standardOptions: any) => {
	const value = map.get(key);
	map.set(key, {
		...value!,
		standardOptions,
	});
	return map;
};

const updateProp = async (oldKey: string, newKey: string, value: BlockProps[string]) => {
	let map = new Map(Object.entries(props.obj));

	if (oldKey !== newKey) {
		map = new Map(Object.entries(replaceKey(map, oldKey, newKey)));
	}

	map = updateObjectValue(map, newKey, {
		value: value.value,
		type: value.type,
	});
	map = updateIsStandard(map, newKey, value.isStandard || false);
	map = updateStandardOptions(map, newKey, value.standardOptions || {});

	emit("update:obj", mapToObject(map));

	return map;
};

const deleteObjectKey = (key: string) => {
	const map = new Map(Object.entries(props.obj));
	const value = map.get(key);
	const path = value?.value;
	map.delete(key);
	emit("update:obj", mapToObject(map));
};

watch([keyBeingEdited, () => props.obj], () => {
	if (keyBeingEdited.value) {
		propDetailsOfKeyBeingEdited.value = props.obj[keyBeingEdited.value];
	} else {
		propDetailsOfKeyBeingEdited.value = null;
	}
});
</script>

<style scoped>
.prop-list-item > div:first-child {
	width: 100%;
}
</style>
