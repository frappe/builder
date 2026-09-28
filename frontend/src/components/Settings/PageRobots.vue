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
				:description="description"
				:show-line-numbers="true"></CodeEditor>
		</div>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { websiteSettings } from "@/data/websiteSettings";
import CodeEditor from "../Controls/CodeEditor.vue";

const guideURL =
	"https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Robots_txt";
const guideLink = `<a href="${guideURL}">${__("Robots.txt Guide")}</a>`;
const description = __(
	"Specify rules to control how search engines interact with your site. For more details, visit {0}.",
	[guideLink],
);
</script>
