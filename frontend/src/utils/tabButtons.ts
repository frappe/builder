// frappe-ui's TabButtons hugs its content; Builder's segmented controls split the
// width they are given. Reaching into the component's markup is the only way, so it
// lives here rather than in every caller.
export const STRETCH_TABS =
	"[&>div]:w-full [&_[data-slot=tab-button]]:flex-1 [&_[data-slot=tab-button]>span]:w-full";

// the smallest icon-only pill frappe-ui draws is 26px square with a 16px icon,
// which stands taller than a row of text-xs labels. This one is 20px with a 12px icon
export const COMPACT_TABS =
	"[&_[data-slot=tab-button]>span]:size-5 [&_[data-slot=tab-button]>span]:p-[3px] [&_[data-slot=tab-button]_[aria-hidden]]:size-3";
