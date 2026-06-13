<template>
	<div class="flex flex-col gap-2">
		<div class="flex flex-col gap-2 rounded-lg">
			<template v-for="(value, name, index) in obj" :key="index">
				<div class="var-list-item relative flex w-full flex-col rounded bg-surface-gray-1 p-2 text-ink-gray-6">
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
									<component
										:is="
											{
												number: LucideNumber,
												string: LucideString,
												boolean: LucideBoolean,
												object: LucideObject,
												array: LucideArray,
											}[value.type] || LucideString
										"
										class="h-4 w-4 text-ink-gray-4" />
									<div class="flex max-w-full flex-col gap-1">
										<p class="text-sm font-medium">{{ name }}</p>
										<p class="max-w-full truncate text-ellipsis text-xs text-ink-gray-4">
											{{ formatInitialValue(value) }}
										</p>
									</div>
								</div>
								<Button
									class="flex-shrink-0 bg-transparent text-xs text-ink-gray-6"
									variant="subtle"
									icon="lucide-x"
									@click="deleteVar(name as string)" />
							</div>
						</template>
						<template #body="{ close }">
							<VarsPopoverContent
								ref="popoverContentItemsRef"
								mode="edit"
								:varName="name as string"
								:varDetails="value"
								@update:var="
									(variable) => {
										updateVar(variable);
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
					" />
			</template>
			<template #body="{ close }">
				<VarsPopoverContent
					ref="popoverContentAddRef"
					:mode="popupMode"
					:varName="keyBeingEdited"
					:varDetails="varDetailsOfKeyBeingEdited"
					@add:var="
						(variable) => {
							addVar(variable);
							close();
						}
					"
					@update:var="updateVar" />
			</template>
		</Popover>
	</div>
</template>

<script setup lang="ts">
import { mapToObject, replaceMapKey } from "@/utils/helpers";
import { Popover } from "frappe-ui";
import { ref, watch } from "vue";
import VarsPopoverContent from "./VarsPopoverContent.vue";

import LucideObject from "~icons/lucide/braces";
import LucideArray from "~icons/lucide/brackets";
import LucideNumber from "~icons/lucide/pi";
import LucideBoolean from "~icons/lucide/toggle-right";
import LucideString from "~icons/lucide/type";

const props = defineProps<{
	obj: BlockVars;
}>();

const emit = defineEmits({
	"update:obj": (obj: BlockVars) => true,
});

const popupMode = ref<"add" | "edit">("add");
const keyBeingEdited = ref<string | null>(null);
const varDetailsOfKeyBeingEdited = ref<BlockVars[string] | null>(null);
const popoverContentAddRef = ref<typeof VarsPopoverContent | null>(null);
const popoverContentItemsRef = ref<Array<typeof VarsPopoverContent | null>>([]);

function formatInitialValue(value: BlockVars[string]) {
	if (value.type === "object" || value.type === "array") {
		return JSON.stringify(value.initialValue ?? (value.type === "array" ? [] : {}));
	}
	return String(value.initialValue ?? "Empty String Value");
}

const addVar = ({ name, value }: { name: string; value: BlockVars[string] }) => {
	const map = new Map(Object.entries(props.obj));
	map.set(name, value);
	popupMode.value = "edit";
	emit("update:obj", mapToObject(map));
};

const replaceKey = (map: Map<string, BlockVars[string]>, oldKey: string, newKey: string) => {
	keyBeingEdited.value = newKey;
	return mapToObject(replaceMapKey(map, oldKey, newKey));
};

const updateVar = ({
	oldVarName,
	newName,
	newValue,
}: {
	oldVarName: string;
	newName: string;
	newValue: BlockVars[string];
}) => {
	let map = new Map(Object.entries(props.obj));

	if (oldVarName !== newName) {
		map = new Map(Object.entries(replaceKey(map, oldVarName, newName)));
	}

	map.set(newName, newValue);
	emit("update:obj", mapToObject(map));
};

const deleteVar = (key: string) => {
	const map = new Map(Object.entries(props.obj));
	map.delete(key);
	emit("update:obj", mapToObject(map));
};

watch([keyBeingEdited, () => props.obj], () => {
	if (keyBeingEdited.value) {
		varDetailsOfKeyBeingEdited.value = props.obj[keyBeingEdited.value];
	} else {
		varDetailsOfKeyBeingEdited.value = null;
	}
});
</script>

<style scoped>
.var-list-item > div:first-child {
	width: 100%;
}
</style>
