import { BuilderVariable } from "@/types/doctypes";
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

	return variables
		.filter((builderVariable: BuilderVariable) => {
			const label = (builderVariable.variable_name || "").toLowerCase();
			const group = (builderVariable.group || "").toLowerCase();
			const queryLower = processedQuery.toLowerCase();
			return queryLower === "" || label.includes(queryLower) || group.includes(queryLower);
		})
		.map((builderVariable: BuilderVariable) => {
			const varName = `var(--${builderVariable.name})`;
			const resolvedLightColor = resolveVariableValue(varName);
			const resolvedDarkColor = resolveVariableValue(varName, true);

			return {
				label: `${builderVariable?.variable_name || ""}`,
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
