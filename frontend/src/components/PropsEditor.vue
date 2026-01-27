<template>
	<div ref="propsEditor" class="flex flex-col gap-2">
		<div class="flex flex-col gap-2 rounded-lg">
			<template v-for="(value, name, index) in sortedProps" :key="index">
				<div
					:key="index"
					class="prop-list-item relative flex w-full flex-col rounded bg-surface-gray-1 p-2 text-ink-gray-6"
					v-if="value.isStandard !== true || shouldDisplayStandardProps">
					<Popover :offset="32" placement="right">
						<template #target="{ open }">
							<div
								class="flex w-full cursor-pointer items-center justify-between"
								@click.stop="
											() => {
												popupMode = 'edit';
												popoverContentItemsRef[index]?.reset({
													keepName: false,
													keepIsStandard: false,
													keepProps: true,
													keepType: false,
												});
												keyBeingEdited = name as string;
												open();
											}">
								<div class="flex w-fit max-w-[60%] items-center gap-2 pl-2">
									<div class="icon">
										<component
											v-if="!value.isStandard"
											:is="
												value.isDynamic
													? value.comesFrom == 'props'
														? LucideGitCommit
														: LucideZap
													: LucideCaseSensitive
											"
											class="h-4 w-4 text-ink-gray-4" />
										<component
											v-if="value.isStandard && value.propOptions?.type"
											:is="
												{
													number: LucideNumber,
													string: LucideString,
													boolean: LucideBoolean,
													select: LucideSelect,
													object: LucideObject,
													array: LucideArray,
													color: LucideColor,
													image: LucideImage,
												}[value.propOptions?.type] || LucideZap
											"
											class="h-4 w-4 text-ink-gray-4" />
									</div>
									<div class="flex max-w-full flex-col gap-1">
										<p class="text-sm font-medium">
											{{ value.label || name }}
										</p>
										<p
											v-if="value.isStandard"
											class="max-w-24 truncate text-ellipsis text-xs text-ink-gray-4">
											{{
												value.propOptions?.options?.defaultValue
													? ["array", "object"].includes(value.propOptions.options.type)
														? JSON.stringify(value.propOptions?.options?.defaultValue)
														: value.propOptions?.options?.defaultValue
													: "No Default Value"
											}}
										</p>
										<p v-else class="max-w-full truncate text-ellipsis text-xs text-ink-gray-4">
											{{ value.value || "No Value" }}
										</p>
									</div>
								</div>
								<div class="flex-shrink-0 gap-1 rounded">
									<BuilderButton
										class="flex-shrink-0 bg-transparent text-xs text-ink-gray-6"
										variant="subtle"
										icon="x"
										@click="deleteObjectKey(name as string)" />
								</div>
							</div>
						</template>
						<template #body="{ open, close }">
							<PropsPopoverContent
								ref="popoverContentItemsRef"
								mode="edit"
								:propName="name as string"
								:propDetails="value"
								@update:prop="
									(prop) => {
										updateProp(prop);
										close();
									}
								" />
						</template>
					</Popover>
				</div>
			</template>
		</div>
		<Popover ref="popOverRef" :offset="24" placement="right">
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
			<template #body="{ open, close }">
				<PropsPopoverContent
					ref="popoverContentAddRef"
					:mode="popupMode"
					:propName="keyBeingEdited"
					:propDetails="propDetailsOfKeyBeingEdited"
					@add:prop="
						(prop) => {
							addProp(prop);
							close();
						}
					"
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
import LucideGitCommit from "~icons/lucide/git-commit-horizontal";
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
// @ts-ignore
import LucideColor from "~icons/lucide/palette";
// @ts-ignore
import LucideImage from "~icons/lucide/image";

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

const sortedProps = computed(() => {
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

const emit = defineEmits({
	"update:obj": (obj: BlockProps) => true,
});

const addProp = async ({ name, value }: { name: string; value: BlockProps[string] }) => {
	const map = new Map(Object.entries(props.obj));
	map.set(name, value);
	popupMode.value = "edit";
	emit("update:obj", mapToObject(map));
	return map;
};

const updateObjectValue = (
	map: Map<string, BlockProps[string]>,
	key: string,
	{
		label,
		value,
		isDynamic,
		comesFrom,
		isPassedDown,
	}: {
		label?: string;
		value: string | null;
		isDynamic: boolean;
		comesFrom: BlockProps[string]["comesFrom"];
		isPassedDown: boolean;
	},
) => {
	if (!value) {
		value = null;
		isDynamic = false;
		comesFrom = null;
	} else {
		value = !isDynamic && typeof value !== "string" ? JSON.stringify(value) : value;
	}

	const oldValue = map.get(key)?.value;
	const oldLabel = map.get(key)?.label;
	const wasDynamic = map.get(key)?.isDynamic;
	const cameFrom = map.get(key)?.comesFrom;
	const wasPassedDown = map.get(key)?.isPassedDown;

	if (
		value === oldValue &&
		label === oldLabel &&
		isDynamic === wasDynamic &&
		comesFrom === cameFrom &&
		isPassedDown === wasPassedDown
	) {
		return map;
	}

	map.set(key, {
		...map.get(key)!,
		label,
		value,
		isDynamic,
		comesFrom,
		isPassedDown,
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

const updatePropOptions = (map: Map<string, BlockProps[string]>, key: string, propOptions: any) => {
	const value = map.get(key);
	map.set(key, {
		...value!,
		propOptions,
	});
	return map;
};

const updateProp = async ({
	oldPropName,
	newName,
	newValue,
}: {
	oldPropName: string;
	newName: string;
	newValue: BlockProps[string];
}) => {
	let map = new Map(Object.entries(props.obj));

	if (oldPropName !== newName) {
		map = new Map(Object.entries(replaceKey(map, oldPropName, newName)));
	}

	map = updateObjectValue(map, newName, {
		label: newValue.label,
		value: newValue.value,
		isDynamic: newValue.isDynamic,
		comesFrom: newValue.comesFrom,
		isPassedDown: newValue.isPassedDown || false,
	});
	map = updateIsStandard(map, newName, newValue.isStandard || false);
	map = updatePropOptions(map, newName, newValue.propOptions || {});
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
