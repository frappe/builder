<template>
	<div class="flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<h3 class="text-base font-medium text-ink-gray-9">Style Tokens</h3>
			<button class="text-sm text-ink-gray-7 hover:text-ink-gray-9" @click="openDialog()">
				<FeatherIcon name="plus" class="size-4" />
			</button>
		</div>
		<div v-if="isLoading" class="flex justify-center py-4">
			<FeatherIcon name="loader" class="size-5 animate-spin text-ink-gray-7" />
		</div>
		<div v-else-if="!tokens.length" class="py-2 text-sm italic text-ink-gray-6">No style tokens found</div>
		<div v-else class="flex flex-col">
			<div
				v-for="token in tokens"
				:key="token.name"
				class="group flex items-center justify-between rounded p-1">
				<div class="flex items-center gap-2">
					<div
						class="size-4 rounded-full border border-outline-gray-2"
						:style="{ backgroundColor: resolveTokenValue(token.value || '') }"></div>
					<div class="flex flex-col">
						<span class="text-p-sm font-medium text-ink-gray-9">{{ token.token_name }}</span>
						<span class="text-xs text-ink-gray-6">
							{{ token.value }}
						</span>
					</div>
				</div>
				<div class="flex gap-2 opacity-0 group-hover:opacity-100">
					<button class="text-ink-gray-7 hover:text-ink-gray-9" @click="openDialog(token)">
						<FeatherIcon name="edit-2" class="size-3" />
					</button>
					<button class="text-ink-gray-7 hover:text-red-600" @click="handleDeleteToken(token)">
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
						loading: isLoading,
						onClick: handleSaveToken,
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
import { StyleToken } from "@/types/Builder/StyleToken";
import { confirm } from "@/utils/helpers";
import { defaultToken, useStyleToken } from "@/utils/useStyleToken";
import { Dialog, FeatherIcon } from "frappe-ui";
import { ref } from "vue";
import { toast } from "vue-sonner";
import ColorInput from "./Controls/ColorInput.vue";

const { resolveTokenValue, createToken, updateToken, deleteToken, isLoading, tokens } = useStyleToken();

const showDialog = ref(false);
const dialogMode = ref<"add" | "edit">("add");
const activeToken = ref<Partial<StyleToken>>({ ...defaultToken });

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

const handleSaveToken = async () => {
	try {
		if (dialogMode.value === "edit") {
			await updateToken(activeToken.value);
			toast.success("Color token updated");
		} else {
			await createToken(activeToken.value);
			toast.success("Color token created");
		}
		showDialog.value = false;
		activeToken.value = { ...defaultToken };
	} catch (error) {
		toast.error((error as Error).message || `Failed to ${dialogMode.value} color token`);
	}
};

const handleDeleteToken = async (token: StyleToken) => {
	const confirmed = await confirm("Are you sure you want to delete this token?");
	if (!confirmed) return;

	try {
		await deleteToken(token.name as string);
		toast.success("Color token deleted");
	} catch (error) {
		toast.error((error as Error).message || "Failed to delete color token");
	}
};
</script>
