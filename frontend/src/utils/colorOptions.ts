import { BuilderVariable } from "@/types/doctypes";
import { filterOptions } from "@/utils/autocompleteOptions";
import { defineComponent, h, shallowRef } from "vue";

export function getColorVariableOptions(
	query: string,
	variables: BuilderVariable[],
	resolveVariableValue: (val: string, dark?: boolean) => string,
	isDark: boolean,
	onEdit?: (variable: BuilderVariable) => void,
) {
	// strip var(--...) syntax, keep the rest of the query as typed
	let processedQuery = query
		.replace(/^\s*(var\()?\s*(--)?/, "")
		.replace(/\)\s*$/, "")
		.trim();

	const searchableLabel = (builderVariable: BuilderVariable) =>
		`${builderVariable.variable_name || ""} ${builderVariable.group || ""}`;

	// the group name is searchable along with the variable name
	const searchableOptions = variables
		.map((builderVariable: BuilderVariable) => ({
			label: searchableLabel(builderVariable),
			variable: builderVariable,
		}))
		// alphabetical, so the options around a match are related ones
		.sort((a, b) => (a.variable.variable_name || "").localeCompare(b.variable.variable_name || ""));

	// the query is the current selection when it is the var() value or the
	// variable's display name (what ColorInput shows on focus): use its full
	// label so filterOptions windows the list around it
	const normalizedQuery = processedQuery.toLowerCase();
	const selectedVariable = variables.find(
		(v) =>
			query.trim() === `var(--${v.name})` || (v.variable_name || "").toLowerCase() === normalizedQuery,
	);
	if (selectedVariable) processedQuery = searchableLabel(selectedVariable);

	return filterOptions(searchableOptions, processedQuery).map(({ variable: builderVariable }) => {
		const varName = `var(--${builderVariable.name})`;
		const resolvedLightColor = resolveVariableValue(varName);
		const resolvedDarkColor = resolveVariableValue(varName, true);

		return {
			label: `${builderVariable.variable_name || ""}`,
			value: varName,
			prefix: shallowRef(
				defineComponent({
					setup() {
						return () =>
							h("div", {
								class: "h-4 w-4 rounded shadow-sm border border-outline-gray-1 flex-shrink-0",
								style: { background: isDark ? resolvedDarkColor : resolvedLightColor },
							});
					},
				}),
			),
			suffix:
				!builderVariable.is_standard && onEdit
					? shallowRef(
							defineComponent({
								setup() {
									return () =>
										h(
											"Button",
											{
												class: "hidden group-hover:inline-block",
												onClick: (e: Event) => {
													onEdit(builderVariable);
												},
											},
											"Edit",
										);
								},
							}),
						)
					: undefined,
		};
	});
}
