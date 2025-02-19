
export interface BuilderPageLibrary{
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
	/**	Library Type : Select	*/
	library_type?: "CSS" | "JS"
	/**	Library URL : Data	*/
	library_url?: string
}