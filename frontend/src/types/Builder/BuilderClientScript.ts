
export interface BuilderClientScript{
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
	/**	Script Type : Autocomplete	*/
	script_type: any
	/**	Script : Code	*/
	script: string
	/**	Public URL : Read Only	*/
	public_url?: string
}