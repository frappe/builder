<template>
	<div class="flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<h3 class="text-base font-medium text-ink-gray-9">Style Tokens</h3>
			<button class="text-sm text-ink-gray-7 hover:text-ink-gray-9" @click="openDialog()">
				<FeatherIcon name="plus" class="size-4" />
			</button>
		</div>
		<div v-if="styleTokens.loading" class="flex justify-center py-4">
			<FeatherIcon name="loader" class="size-5 animate-spin text-ink-gray-7" />
		</div>
		<div v-else-if="!styleTokens.data?.length" class="py-2 text-sm italic text-ink-gray-6">
			No style tokens found
		</div>
		<div v-else class="flex flex-col">
			<div
				v-for="token in styleTokens.data"
				:key="token.name"
				class="group flex items-center justify-between rounded p-1">
				<div class="flex items-center gap-2">
					<div
						class="size-4 rounded-full border border-outline-gray-2"
						:style="{ backgroundColor: token.value }"></div>
					<div class="flex flex-col">
						<span class="text-p-sm font-medium text-ink-gray-9">{{ token.token_name }}</span>
						<span class="text-xs text-ink-gray-6">{{ token.value }}</span>
					</div>
				</div>
				<div class="flex gap-2 opacity-0 group-hover:opacity-100">
					<button class="text-ink-gray-7 hover:text-ink-gray-9" @click="openDialog(token)">
						<FeatherIcon name="edit-2" class="size-3" />
					</button>
					<button class="text-ink-gray-7 hover:text-red-600" @click="deleteToken(token)">
						<FeatherIcon name="trash" class="size-3" />
					</button>
				</div>
			</div>
		</div>

		<Dialog
			v-model="showDialog"
			:options="{
				title: dialogMode === 'edit' ? 'Edit Style Token' : 'New Style Token',
				size: 'sm',
				actions: [
					{
						label: dialogMode === 'edit' ? 'Update' : 'Create',
						variant: 'solid',
						loading: styleTokens.loading,
						onClick: saveToken,
					},
				],
			}">
			<template #body-content>
				<div class="flex flex-col gap-4">
					<BuilderInput
						type="text"
						v-model="activeToken.token_name"
						label="Token Name"
						required
						:autofocus="true"
						placeholder="e.g., primary, accent, background"
						:hideClearButton="true" />
					<div class="flex flex-col gap-1.5">
						<InputLabel>Color Value</InputLabel>
						<ColorInput v-model="activeToken.value" class="relative" />
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import styleTokens from "@/data/styleTokens";
import { confirm } from "@/utils/helpers";
import { Dialog, FeatherIcon } from "frappe-ui";
import { ref } from "vue";
import { toast } from "vue-sonner";
import ColorInput from "./Controls/ColorInput.vue";

type StyleToken = {
	name?: string;
	token_name: string;
	type: string;
	value: `#${string}`;
};

const defaultToken: StyleToken = {
	token_name: "",
	type: "color",
	value: "#000000",
};

const showDialog = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const activeToken = ref<StyleToken>({ ...defaultToken });

const openDialog = (token?: StyleToken) => {
	if (token) {
		dialogMode.value = "edit";
		activeToken.value = { ...token };
	} else {
		dialogMode.value = "add";
		activeToken.value = { ...defaultToken };
	}
	showDialog.value = true;
};

const saveToken = () => {
	if (!activeToken.value.token_name || !activeToken.value.value) {
		toast.error("Please fill in all fields");
		return;
	}

	const request =
		dialogMode.value === "edit"
			? styleTokens.setValue.submit({
					name: activeToken.value.name,
					token_name: activeToken.value.token_name,
					value: activeToken.value.value,
				})
			: styleTokens.insert.submit({
					token_name: activeToken.value.token_name,
					value: activeToken.value.value,
				});

	request
		.then(() => {
			toast.success(`Color token ${dialogMode.value === "edit" ? "updated" : "created"}`);
			showDialog.value = false;
			activeToken.value = { ...defaultToken };
		})
		.catch((error: Error) => {
			toast.error(error.message || `Failed to ${dialogMode.value} color token`);
		});
};

const deleteToken = async (token: StyleToken) => {
	const confirmed = await confirm("Are you sure you want to delete this token?");
	if (!confirmed) return;

	try {
		await styleTokens.delete.submit(token.name);
		toast.success("Color token deleted");
	} catch (error) {
		toast.error((error as Error).message || "Failed to delete color token");
	}
};
</script>
