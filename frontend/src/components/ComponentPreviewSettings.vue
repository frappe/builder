<template>
	<div class="flex w-72 flex-col gap-3 rounded bg-surface-base p-4 shadow-lg">
		<div class="text-sm text-ink-gray-8">Preview Details</div>
		<BasePropertyControl
			propertyKey="componentName"
			label="Label"
			:getModelValue="() => componentName"
			:setModelValue="componentController.setComponentName" />
		<BasePropertyControl
			propertyKey="category"
			label="Category"
			:getModelValue="() => componentCategory"
			:setModelValue="componentController.setComponentCategory" />
		<BasePropertyControl
			propertyKey="image"
			label="Image"
			:component="ImageUploadInput"
			labelPosition="top"
			:getModelValue="() => componentPreview"
			:setModelValue="componentController.setComponentPreview" />

		<BasePropertyControl
			propertyKey="category"
			label="Width"
			:getModelValue="() => componentPreviewWidth"
			:setModelValue="componentController.setComponentPreviewWidth" />
		<BasePropertyControl
			propertyKey="category"
			label="Height"
			:getModelValue="() => componentPreviewHeight"
			:setModelValue="componentController.setComponentPreviewHeight" />
		<!-- <div class="grid grid-cols-2 gap-3">
			<BuilderInput
				type="number"
				label="Width"
				min="1"
				max="2"
				:modelValue="componentPreviewWidth"
				@update:modelValue="componentController.setComponentPreviewWidth" />
			<BuilderInput
				type="number"
				label="Height"
				min="1"
				max="2"
				:modelValue="componentPreviewHeight"
				@update:modelValue="componentController.setComponentPreviewHeight" />
		</div> -->
	</div>
</template>

<script setup lang="ts">
import componentController from "@/utils/componentController";
import ImageUploadInput from "./ImageUploadInput.vue";
import BasePropertyControl from "./Controls/BasePropertyControl.vue";

const { componentName, componentCategory, componentPreview, componentPreviewWidth, componentPreviewHeight } =
	componentController;
</script>
