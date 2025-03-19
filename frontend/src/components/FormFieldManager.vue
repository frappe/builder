<template>
	<Dropdown
		:options="[
			{
				label: 'Text',
				value: 'text',
				onClick: () => addField('text'),
			},
			{
				label: 'Select',
				value: 'select',
				onClick: () => addField('select'),
			},
		]">
		<template v-slot="{ open }">
			<BuilderButton class="w-full text-2xs ring-2 ring-inset ring-blue-400" @click="open">
				Add Field
			</BuilderButton>
		</template>
	</Dropdown>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import getBlockTemplate from "@/utils/blockTemplate";
import { Dropdown } from "frappe-ui";

const props = defineProps<{
	block: Block;
}>();

const addField = (type: string) => {
	if (type === "text") {
		props.block.addChild(
			getBlockTemplate("input", {
				type: "text",
			}),
		);
	} else if (type === "select") {
		props.block.addChild(
			getBlockTemplate("select", {
				options: [
					{
						label: "Option 1",
						value: "option_1",
					},
					{
						label: "Option 2",
						value: "option_2",
					},
				],
			}),
		);
	}
};
</script>
