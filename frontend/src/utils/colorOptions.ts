import { BuilderToken } from "@/types/doctypes";
import { filterOptions } from "@/utils/autocompleteOptions";
import { defineComponent, h, shallowRef } from "vue";

export function getColorVariableOptions(
	query: string,
	variables: BuilderToken[],
	resolveVariableValue: (val: string, dark?: boolean) => string,
	isDark: boolean,
	onEdit?: (variable: BuilderToken) => void,
) {
	// strip var(--...) syntax, keep the rest of the query as typed
	let processedQuery = query
		.replace(/^\s*(var\()?\s*(--)?/, "")
		.replace(/\)\s*$/, "")
		.trim();

	const searchableLabel = (builderToken: BuilderToken) =>
		`${builderToken.token_name || ""} ${builderToken.group || ""}`;

	// the group name is searchable along with the token name
	const searchableOptions = variables
		.map((builderToken: BuilderToken) => ({
			label: searchableLabel(builderToken),
			variable: builderToken,
		}))
		// alphabetical, so the options around a match are related ones
		.sort((a, b) => (a.variable.token_name || "").localeCompare(b.variable.token_name || ""));

	// the query is the current selection when it is the var() value or the
	// token's display name (what ColorInput shows on focus): use its full
	// label so filterOptions windows the list around it
	const normalizedQuery = processedQuery.toLowerCase();
	const selectedVariable = variables.find(
		(v) => query.trim() === `var(--${v.name})` || (v.token_name || "").toLowerCase() === normalizedQuery,
	);
	if (selectedVariable) processedQuery = searchableLabel(selectedVariable);

	return filterOptions(searchableOptions, processedQuery).map(({ variable: builderToken }) => {
		const varName = `var(--${builderToken.name})`;
		const resolvedLightColor = resolveVariableValue(varName);
		const resolvedDarkColor = resolveVariableValue(varName, true);

		return {
			label: `${builderToken.token_name || ""}`,
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
				!builderToken.is_standard && onEdit
					? shallowRef(
							defineComponent({
								setup() {
									return () =>
										h(
											"Button",
											{
												class: "hidden group-hover:inline-block",
												onClick: (e: Event) => {
													onEdit(builderToken);
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
