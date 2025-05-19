<template>
	<Menu
		class="fixed z-50 h-fit w-fit min-w-[120px] rounded-md bg-surface-white p-1 shadow-xl"
		:style="{ top: y + 'px', left: x + 'px' }"
		ref="menu">
		<MenuItems static class="text-sm">
			<MenuItem
				v-slot="{ active, disabled }"
				class="block cursor-pointer rounded-sm px-3 py-1 text-ink-gray-9"
				:disabled="option.disabled && option.disabled()"
				v-for="(option, index) in options"
				v-show="!option.condition || option.condition()">
				<div
					@click.prevent.stop="(!option.condition || option.condition()) && handleClick(option.action)"
					:class="{
						'text-gray-900': !disabled,
						'bg-surface-gray-4': active,
						'!cursor-default !text-ink-gray-4': disabled,
					}">
					{{ option.label }}
				</div>
			</MenuItem>
		</MenuItems>
	</Menu>
</template>
<script setup lang="ts">
import { Menu, MenuItem, MenuItems } from "@headlessui/vue";
import { computed, ref } from "vue";

const menu = ref(null) as unknown as typeof Menu;

const props = withDefaults(
	defineProps<{
		posX: number;
		posY: number;
		options: ContextMenuOption[];
	}>(),
	{
		options: () => [],
	},
);

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
