import {
	computed,
	customRef,
	effect,
	effectScope,
	getCurrentScope,
	isProxy,
	isReactive,
	isReadonly,
	isRef,
	markRaw,
	onScopeDispose,
	reactive,
	readonly,
	ref,
	shallowReactive,
	shallowReadonly,
	shallowRef,
	stop,
	toRaw,
	toRef,
	toRefs,
	triggerRef,
	unref,
	watch,
} from "@vue/reactivity";

const reactivity = {
	computed,
	customRef,
	effect,
	effectScope,
	getCurrentScope,
	isProxy,
	isReactive,
	isReadonly,
	isRef,
	markRaw,
	onScopeDispose,
	reactive,
	readonly,
	ref,
	shallowReactive,
	shallowReadonly,
	shallowRef,
	stop,
	toRaw,
	toRef,
	toRefs,
	triggerRef,
	unref,
	watch,
	// Alias for Vue users — implemented by `effect` in @vue/reactivity
	watchEffect: effect,
};

declare global {
	interface Window {
		reactivity: typeof reactivity;
	}
}

if (typeof window !== "undefined") {
	window.reactivity = reactivity;
	Object.assign(window, reactivity);
}

export default reactivity;
