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
	let processedQuery = query.replace(/^(--|var|\s+)/, "");
	processedQuery = processedQuery.replace(/^--|\(|\s+/g, "");

	// the group name is searchable along with the variable name
	const searchableOptions = variables.map((builderVariable: BuilderVariable) => ({
		label: `${builderVariable.variable_name || ""} ${builderVariable.group || ""}`,
		variable: builderVariable,
	}));

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
