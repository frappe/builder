<template>
	<div class="flex flex-col gap-5">
		<div class="flex justify-between">
			<label class="text-p-base-medium w-fit shrink-0 text-ink-gray-8">
				在编辑器中执行区块客户端脚本
			</label>
			<Select
				class="!w-[200px]"
				:modelValue="builderSettings.doc?.execute_block_scripts_in_editor"
				@update:modelValue="
					(value) => builderStore.updateBuilderSettings('execute_block_scripts_in_editor', value)
				"
				:options="[
					{ label: '不执行', value: 'Don\'t Execute' },
					{ label: '受限', value: 'Restricted' },
					{ label: '不受限', value: 'Unrestricted' },
				]" />
		</div>
		<Switch
			size="sm"
			label="阻止点击模拟"
			description="阻止编辑器为带有区块客户端脚本的区块模拟点击事件。"
			:modelValue="Boolean(builderSettings.doc?.restrict_click_handlers)"
			@update:modelValue="
				(val: Boolean) => {
					builderStore.updateBuilderSettings('restrict_click_handlers', val);
				}
			" />
		<div class="flex flex-col gap-2">
			<p class="text-p-sm text-ink-gray-7">
				注意：区块脚本在沙箱环境中执行。可能存在限制，且无法完全还原线上站点的行为。执行不受信任的脚本可能存在安全风险。
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { Select, Switch } from "frappe-ui";

const builderStore = useBuilderStore();
</script>
