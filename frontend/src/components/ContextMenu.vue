<template>
		<Menu
			class="fixed z-50 h-fit w-fit min-w-[120px] rounded-lg bg-white p-1 shadow-xl dark:bg-zinc-900"
			:style="{ top: posY + 'px', left: posX + 'px' }">
			<MenuItems static class="text-sm">
				<MenuItem
					v-slot="{ active, disabled }"
					class="rounded-md px-3 py-1 dark:text-zinc-50 block cursor-pointer"
					v-for="(option, index) in options"
					:disabled="option.condition && !option.condition()">
					<div @click.prevent.stop="(!option.condition || option.condition()) && handleClick(option.action)"
						:class="{
							'text-gray-900': !disabled,
							'bg-gray-200 dark:bg-zinc-700': active,
							'text-gray-400 dark:text-zinc-500': disabled
						}">
						{{ option.label }}
					</div>
				</MenuItem>
			</MenuItems>
		</Menu>
</template>
<script setup lang="ts">
import { Menu, MenuItem, MenuItems } from "@headlessui/vue";

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
