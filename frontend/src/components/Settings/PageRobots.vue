<template>
	<div class="flex h-full flex-col items-center gap-5 overflow-y-auto">
		<div class="flex w-full max-w-[500px] gap-4">
			<CodeEditor
				class="overscroll-none"
				:modelValue="websiteSettings.doc.robots_txt"
				@save="
					(val) => {
						websiteSettings.setValue.submit({
							robots_txt: val,
						});
					}
				"
				type="Python"
				height="60vh"
				label="robot.txt"
				:showSaveButton="true"
				description='Specify rules to control how search engines interact with your site.
				For more details, visit <a href="https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Robots_txt">Robots.txt Guide.</a>'
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>
<script setup lang="ts">
import { websiteSettings } from "@/data/websiteSettings";
import CodeEditor from "../Controls/CodeEditor.vue";
</script>
