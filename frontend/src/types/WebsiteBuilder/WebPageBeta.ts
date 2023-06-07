export interface WebPageBeta {
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
	/**	Page Name : Data	*/
	page_name: string
	/**	Page Title : Data	*/
	page_title?: string
	/**	Route : Data	*/
	route?: string
	/**	Published : Check	*/
	published?: 0 | 1
	/**	Blocks : JSON	*/
	blocks?: any
	/**	Preview : Attach Image	*/
	preview?: string
}