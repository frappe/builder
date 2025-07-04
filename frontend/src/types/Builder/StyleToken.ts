
export interface StyleToken{
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
	/**	Token Name : Data	*/
	token_name?: string
	/**	Type : Select	*/
	type?: "Color" | "Spacing"
	/**	Value : Data	*/
	value?: string
}