
export interface BlockTemplate{
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
	/**	Template Name : Data	*/
	template_name: string
	/**	Block : JSON	*/
	block: any
	/**	Preview : Data	*/
	preview: string
	/**	Category : Select	*/
	category?: "Basic" | "Structure"
}