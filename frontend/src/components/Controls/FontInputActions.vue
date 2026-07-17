<template>
	<div class="flex flex-col">
		<Button
			v-if="canSaveAsToken"
			iconLeft="lucide-plus"
			variant="ghost"
			class="w-full justify-start rounded-none text-sm text-ink-gray-8"
			@click="openTokenDialog">
			Save as Token
		</Button>
		<FontUploader @change="$emit('change')" />
		<NewBuilderToken v-model="showTokenDialog" :variable="newToken" @success="handleTokenSaved" />
	</div>
</template>

<script setup lang="ts">
import FontUploader from "@/components/Controls/FontUploader.vue";
import NewBuilderToken from "@/components/Modals/NewBuilderToken.vue";
import { BuilderToken } from "@/types/doctypes";
import blockController from "@/utils/blockController";
import { Button } from "frappe-ui";
import { computed, ref } from "vue";

defineEmits(["change"]);

const showTokenDialog = ref(false);
const newToken = ref<Partial<BuilderToken> | null>(null);

const currentFont = computed(() => blockController.getFontFamily() as string | undefined);

// only plain families can be promoted; a value already bound to a var() is a token
const canSaveAsToken = computed(
	() => !!currentFont.value && !currentFont.value.startsWith("var(--") && !currentFont.value.startsWith("--"),
);

const openTokenDialog = () => {
	newToken.value = { value: currentFont.value || "", type: "Font" };
	showTokenDialog.value = true;
};

const handleTokenSaved = (savedToken: BuilderToken) => {
	blockController.setFontFamily(`var(--${savedToken.name})`);
};
</script>
