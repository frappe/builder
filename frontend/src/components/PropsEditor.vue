<template>
	<div ref="propsEditor" class="flex flex-col gap-2">
		<div class="flex flex-col gap-2 rounded-lg">
			<template v-for="(value, name, index) in props.obj" :key="index">
				<div
					class="prop-list-item relative flex w-full flex-col rounded bg-surface-gray-1 p-2 text-ink-gray-6">
					<Popover :offset="32" placement="right">
						<template #target="{ open }">
							<div
								class="flex w-full cursor-pointer items-center justify-between"
								@click.stop="
									() => {
										popupMode = 'edit';
										popoverContentItemsRef[index]?.reset({
											keepName: false,
											keepProps: true,
											keepType: false,
										});
										keyBeingEdited = name as string;
										open();
									}
								">
								<div class="flex w-fit max-w-[60%] items-center gap-2 pl-2">
									<div class="icon">
										<component
											v-if="value.propOptions?.type"
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
										<p class="text-sm-medium">
											{{ value.label || name }}
										</p>
										<p class="max-w-24 truncate text-ellipsis text-xs text-ink-gray-4">
											{{
												value.propOptions?.options?.defaultValue
													? ["array", "object"].includes(value.propOptions.options.type)
														? JSON.stringify(value.propOptions?.options?.defaultValue)
														: value.propOptions?.options?.defaultValue
													: "No Default Value"
											}}
										</p>
									</div>
								</div>
								<div class="flex-shrink-0 gap-1 rounded">
									<Button
										class="flex-shrink-0 bg-transparent text-xs text-ink-gray-6"
										variant="subtle"
										icon="lucide-x"
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
				<Button
					class="w-full"
					variant="subtle"
					label="Add"
					@click="
						() => {
							popoverContentAddRef?.reset({
								keepName: false,
								keepProps: false,
								keepType: false,
							});
							keyBeingEdited = null;
							popupMode = 'add';
							open();
						}
					"></Button>
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
import { ref, useAttrs, watch } from "vue";

import LucideObject from "~icons/lucide/braces";
import LucideArray from "~icons/lucide/brackets";
import LucideSelect from "~icons/lucide/chevrons-up-down";
import LucideImage from "~icons/lucide/image";
import LucideColor from "~icons/lucide/palette";
import LucideNumber from "~icons/lucide/pi";
import LucideBoolean from "~icons/lucide/toggle-right";
import LucideString from "~icons/lucide/type";
import LucideZap from "~icons/lucide/zap";

import { Popover } from "frappe-ui";
import PropsPopoverContent from "./PropsPopoverContent.vue";

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

const replaceKey = (map: Map<string, BlockProps[string]>, oldKey: string, newKey: string) => {
	keyBeingEdited.value = newKey;
	return mapToObject(replaceMapKey(map, oldKey, newKey));
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

	map.set(newName, {
		...map.get(newName)!,
		...newValue,
		isStandard: true,
		isDynamic: false,
		isPassedDown: true,
		comesFrom: null,
		value: null,
	});
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
