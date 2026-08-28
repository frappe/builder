<template>
	<div class="group flex hover:gap-1">
		<div v-for="user in builderStore.viewers" :key="user.fullname">
			<Tooltip :text="currentlyViewedByText" :hoverDelay="0.6" arrow-class="mb-3">
				<div class="ml-[-10px] h-6 w-6 cursor-pointer transition-all group-hover:ml-0">
					<img
						class="h-full w-full rounded-full border-2 border-orange-400 object-cover shadow-sm"
						:title="user.fullname"
						:src="user.image"
						v-if="user.image" />
					<div
						v-else
						:title="user.fullname"
						class="grid h-full w-full place-items-center rounded-full border-2 border-orange-400 bg-gray-400 text-sm text-gray-700 shadow-sm">
						{{ user.fullname.charAt(0) }}
					</div>
				</div>
			</Tooltip>
		</div>
	</div>
</template>
<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const builderStore = useBuilderStore();

const currentlyViewedByText = computed(() => {
	const names = builderStore.viewers.map((viewer) => viewer.fullname).map((name) => name.split(" ")[0]);
	const count = names.length;
	if (count === 0) {
		return "";
	} else if (count === 1) {
		return `${names[0]}`;
	} else if (count === 2) {
		return `${names.join(" & ")}`;
	} else {
		return __("{0} & {1} others", [names.slice(0, 2).join(", "), count - 2]);
	}
});
</script>
