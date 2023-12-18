
export interface BuilderSettings{
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
	/**	Script : Code - Global script that will be loaded with every page built with Frappe Builder	*/
	script?: string
	/**	Script Public URL : Read Only	*/
	script_public_url?: string
	/**	Style : Code - Global style that will be loaded with every page built with Frappe Builder	*/
	style?: string
	/**	Style Public URL : Read Only	*/
	style_public_url?: string
}