<template>
	<div ref="objectEditor" class="flex flex-col gap-2" @paste="pasteObj">
		<div v-for="(value, key, index) in obj" :key="index" class="flex gap-2">
			<div class="min-w-0 flex-1">
				<BuilderInput
					placeholder="Property"
					:modelValue="key"
					@update:modelValue="(val: string) => replaceKey(key, val)" />
			</div>
			<DynamicValueDropdown
				v-if="allowDynamicValues"
				class="min-w-0 flex-1"
				:modelValue="value"
				:dynamicValue="getDynamicValueForKey(key)"
				@update:modelValue="(val: string) => updateObjectValue(key, val)"
				@setDynamicValue="(val) => setDynamicValueForKey(key, val.key, val.comesFrom)"
				@clearDynamicValue="() => clearDynamicValueForKey(key)" />
			<div v-else class="min-w-0 flex-1">
				<BuilderInput
					placeholder="Value"
					:modelValue="value"
					@update:modelValue="(val: string) => updateObjectValue(key, val)" />
			</div>
			<Button
				class="flex-shrink-0 text-xs"
				variant="subtle"
				icon="lucide-x"
				@click="deleteObjectKey(key as string)"></Button>
		</div>
		<Button variant="outline" label="Add" @click="addObjectKey"></Button>
		<p class="rounded-sm bg-surface-gray-1 p-2 text-xs text-ink-gray-7" v-show="description">
			<span v-html="description"></span>
		</p>
	</div>
</template>
<script setup lang="ts">
import DynamicValueDropdown from "@/components/DynamicValueDropdown.vue";
import blockController from "@/utils/blockController";
import { mapToObject, replaceMapKey } from "@/utils/helpers";
import { nextTick, ref } from "vue";

const props = defineProps<{
	obj: Record<string, string>;
	description?: string;
	allowDynamicValues?: boolean;
}>();

const emit = defineEmits({
	"update:obj": (obj: Record<string, string>) => true,
});

const getDynamicValueForKey = (key: string) => {
	const block = blockController.getFirstSelectedBlock();
	if (!block) {
		return { key: "", comesFrom: "dataScript" as BlockDataKey["comesFrom"] };
	}
	const dataKeyObj = block.getDynamicValues().find((obj) => obj.type === "attribute" && obj.property === key);
	return {
		key: dataKeyObj?.key || "",
		comesFrom: dataKeyObj?.comesFrom || ("dataScript" as BlockDataKey["comesFrom"]),
	};
};

const setDynamicValueForKey = (attrKey: string, dynamicKey: string, comesFrom: BlockDataKey["comesFrom"]) => {
	blockController.getSelectedBlocks().forEach((block) => {
		block.setDynamicValue(attrKey, "attribute", dynamicKey, comesFrom);
	});
	updateObjectValue(attrKey, dynamicKey);
};

const clearDynamicValueForKey = (attrKey: string) => {
	blockController.getSelectedBlocks().forEach((block) => {
		block.removeDynamicValue(attrKey, "attribute");
	});
};

const migrateDynamicValueKey = (oldKey: string, newKey: string) => {
	if (!props.allowDynamicValues || oldKey === newKey) return;
	blockController.getSelectedBlocks().forEach((block) => {
		const dataKeyObj = block
			.getDynamicValues()
			.find((obj) => obj.type === "attribute" && obj.property === oldKey);
		if (!dataKeyObj?.key) return;
		block.removeDynamicValue(oldKey, "attribute");
		block.setDynamicValue(newKey, "attribute", dataKeyObj.key, dataKeyObj.comesFrom);
	});
};

const addObjectKey = async () => {
	const map = new Map(Object.entries(props.obj));
	map.set("", "");
	emit("update:obj", mapToObject(map));
	await nextTick();
	const inputs = objectEditor.value?.querySelectorAll("input");
	if (inputs) {
		const lastInput = inputs[inputs.length - 2];
		lastInput.focus();
	}
};

const updateObjectValue = (key: string, value: string) => {
	const map = new Map(Object.entries(props.obj));
	map.set(key, value);
	emit("update:obj", mapToObject(map));
};

const replaceKey = (oldKey: string, newKey: string) => {
	const map = new Map(Object.entries(props.obj));
	migrateDynamicValueKey(oldKey, newKey);
	emit("update:obj", mapToObject(replaceMapKey(map, oldKey, newKey)));
};

const deleteObjectKey = (key: string) => {
	const map = new Map(Object.entries(props.obj));
	map.delete(key);
	if (props.allowDynamicValues) {
		blockController.getSelectedBlocks().forEach((block) => {
			block.removeDynamicValue(key, "attribute");
		});
	}
	emit("update:obj", mapToObject(map));
};

const objectEditor = ref<HTMLElement | null>(null);

const pasteObj = (e: ClipboardEvent) => {
	const text = e.clipboardData?.getData("text/plain");
	if (text) {
		if (!text.includes(":")) return;
		e.preventDefault();
		const map = new Map(Object.entries(props.obj));
		try {
			const objString = text.match(/{[^{}]+}/)?.[0];
			if (!objString) throw new Error("Invalid object");
			const obj = new Function("return " + objString)();
			if (typeof obj === "object") {
				for (const [key, value] of Object.entries(obj)) {
					map.set(key, value as string);
				}
				map.delete("");
			}
		} catch (e) {
			const lines = text.split(";");
			for (const line of lines) {
				const [key, value] = line.split(":");
				if (!key || !value) continue;
				map.set(key.trim(), value.replace(";", "").trim());
			}
			map.delete("");
		}
		emit("update:obj", mapToObject(map));
	}
};
</script>
