<template>
	<div class="flex h-full flex-col items-center gap-5 overflow-y-auto">
		<div class="flex h-full w-full flex-1 flex-col gap-4">
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
				height="100%"
				label="robot.txt"
				:showSaveButton="true"
				description='指定控制搜索引擎如何与您的站点交互的规则。
				了解更多详情，请访问 <a href="https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Robots_txt">Robots.txt 指南。</a>'
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>
<script setup lang="ts">
import { websiteSettings } from "@/data/websiteSettings";
import CodeEditor from "../Controls/CodeEditor.vue";
</script>
