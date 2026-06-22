// Shared visual language for inline-editable tables (Variable Manager, Redirects).
// Keeping these together means a text cell and its input swap with zero layout shift.

// cell metrics shared by the static text and the editable input
export const cellBoxClass = "w-full min-w-0 rounded-sm px-2 py-1 text-sm";

// the focus: variants out-rank @tailwindcss/forms' blue [type='text']:focus ring/border
export const editableInputClass =
	"border-none bg-surface-base text-ink-gray-8 outline-none ring-2 ring-outline-gray-3 placeholder:text-ink-gray-4 focus:outline-none focus:ring-2 focus:ring-outline-gray-3";
