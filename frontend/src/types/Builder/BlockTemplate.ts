
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
	/**	Preview Width : Int	*/
	preview_width?: number
	/**	Preview Height : Int	*/
	preview_height?: number
	/**	Category : Select	*/
	category?: "Structure" | "Basic" | "Typography" | "Basic Forms" | "Form parts" | "Media" | "Advanced"
	/**	Order : Int	*/
	order?: number
}