
export interface BuilderVariable{
	creation: string
	name: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Is Standard : Check	*/
	is_standard?: 0 | 1
	/**	Variable Name : Data	*/
	variable_name: string
	/**	Type : Select	*/
	type?: "Color" | "Spacing"
	/**	Value : Data	*/
	value: string
}