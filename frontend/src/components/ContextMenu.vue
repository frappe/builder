<template>
	<div
		class="fixed z-30 h-fit w-fit min-w-[120px] rounded-lg bg-white p-1 shadow-xl dark:bg-zinc-900"
		:style="{ top: posY + 'px', left: posX + 'px' }">
		<ul class="text-sm">
			<li
				class="rounded-md px-3 py-1 text-gray-900 dark:text-zinc-50"
				v-for="(option, index) in options"
				:key="index"
				@click.prevent.stop="(!option.condition || option.condition()) && handleClick(option.action)"
				:class="{
					'cursor-pointer hover:bg-gray-200 hover:dark:bg-zinc-700': !option.condition || option.condition(),
					'text-gray-400 dark:text-zinc-500': option.condition && !option.condition(),
				}">
				{{ option.label }}
			</li>
		</ul>
	</div>
</template>
<script setup lang="ts">
interface ContextMenuOption {
	label: string;
	action: CallableFunction;
	condition?: () => boolean;
}

const props = defineProps({
	posX: Number,
	posY: Number,
	options: Array as () => ContextMenuOption[],
});

const emit = defineEmits({
	select: (action: CallableFunction) => action,
});

const handleClick = (action: CallableFunction) => {
	emit("select", action);
};
</script>
