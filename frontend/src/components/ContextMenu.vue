<template>
	<Menu
		class="fixed z-50 h-fit w-fit min-w-[120px] rounded-lg bg-white p-1 shadow-xl dark:bg-zinc-900"
		:style="{ top: y + 'px', left: x + 'px' }"
		ref="menu">
		<MenuItems static class="text-sm">
			<MenuItem
				v-slot="{ active, disabled }"
				class="block cursor-pointer rounded-md px-3 py-1 dark:text-zinc-50"
				v-for="(option, index) in options"
				v-show="!option.condition || option.condition()">
				<div
					@click.prevent.stop="(!option.condition || option.condition()) && handleClick(option.action)"
					:class="{
						'text-gray-900': !disabled,
						'bg-gray-200 dark:bg-zinc-700': active,
						'text-gray-400 dark:text-zinc-500': disabled,
					}">
					{{ option.label }}
				</div>
			</MenuItem>
		</MenuItems>
	</Menu>
</template>
<script setup lang="ts">
import { Menu, MenuItem, MenuItems } from "@headlessui/vue";
import { Ref, computed, ref } from "vue";

const menu = ref(null) as unknown as typeof Menu;

interface ContextMenuOption {
	label: string;
	action: CallableFunction;
	condition?: () => boolean;
}

const props = defineProps({
	posX: {
		type: Number,
		required: true,
	},
	posY: {
		type: Number,
		required: true,
	},
	options: Array as () => ContextMenuOption[],
});

const x = computed(() => {
	const menuWidth = menu.value?.$el.clientWidth;
	const windowWidth = window.innerWidth;
	const diff = windowWidth - (props.posX + menuWidth);
	if (diff < 0) {
		return props.posX + diff - 10;
	}
	return props.posX;
});

const y = computed(() => {
	const menuHeight = menu.value?.$el.clientHeight;
	const windowHeight = window.innerHeight;
	const diff = windowHeight - (props.posY + menuHeight);
	if (diff < 0) {
		return props.posY + diff - 10;
	}
	return props.posY;
});

const emit = defineEmits({
	select: (action: CallableFunction) => action,
});

const handleClick = (action: CallableFunction) => {
	emit("select", action);
};
</script>
