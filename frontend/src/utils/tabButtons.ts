// frappe-ui's TabButtons hugs its content; Builder's segmented controls split the
// width they are given. Reaching into the component's markup is the only way, so it
// lives here rather than in every caller.
export const STRETCH_TABS =
	"[&>div]:w-full [&_[data-slot=tab-button]]:flex-1 [&_[data-slot=tab-button]>span]:w-full";
