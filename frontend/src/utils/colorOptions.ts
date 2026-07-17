import { BuilderToken } from "@/types/doctypes";
import { defineComponent, h, shallowRef } from "vue";

export function getColorVariableOptions(
	query: string,
	variables: BuilderToken[],
	resolveVariableValue: (val: string, dark?: boolean) => string,
	isDark: boolean,
	onEdit?: (variable: BuilderToken) => void,
) {
	let processedQuery = query.replace(/^(--|var|\s+)/, "");
	processedQuery = processedQuery.replace(/^--|\(|\s+/g, "");

	return variables
		.filter((builderToken: BuilderToken) => {
			// legacy rows have a blank or lowercase type; treat them as colors
			if ((builderToken.type || "Color").toLowerCase() !== "color") return false;
			const label = (builderToken.token_name || "").toLowerCase();
			const group = (builderToken.group || "").toLowerCase();
			const queryLower = processedQuery.toLowerCase();
			return queryLower === "" || label.includes(queryLower) || group.includes(queryLower);
		})
		.map((builderToken: BuilderToken) => {
			const varName = `var(--${builderToken.name})`;
			const resolvedLightColor = resolveVariableValue(varName);
			const resolvedDarkColor = resolveVariableValue(varName, true);

			return {
				label: `${builderToken?.token_name || ""}`,
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
