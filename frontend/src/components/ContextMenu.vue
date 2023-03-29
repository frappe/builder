<template>
	<div class="w-fit h-fit min-w-[120px] p-1 rounded-lg fixed bg-white dark:bg-zinc-900 shadow-xl z-30"
		:style="{ top: posY + 'px', left: posX + 'px' }">
		<ul class="text-sm">
			<li class="px-3 py-1 text-gray-900 dark:text-zinc-50  rounded-md"
				v-for="(option, index) in options" :key="index" @click.prevent.stop="(!option.condition || option.condition()) && handleClick(option.action)" :class="{
					'hover:bg-gray-200 hover:dark:bg-zinc-700 cursor-pointer': !option.condition || option.condition(),
					'text-gray-400 dark:text-zinc-500': option.condition && !option.condition(),
				}">
				{{ option.label }}
			</li>
		</ul>
	</div>
</template>
<script setup>
const props = defineProps({
	posX: Number,
	posY: Number,
	options: Array,
});

const emit = defineEmits({
	select: (action) => action
});

const handleClick = (action) => {
	emit('select', action);
}
</script>