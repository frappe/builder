
export interface WebPageComponent{
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
	/**	Component Name : Data	*/
	component_name?: string
	/**	Block : JSON	*/
	block?: any
	/**	Icon : Data	*/
	icon?: string
	/**	Is Dynamic : Check	*/
	is_dynamic?: 0 | 1
	/**	Preview Image : Attach Image	*/
	preview_image?: string
}