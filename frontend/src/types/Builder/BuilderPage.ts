import { BuilderPageClientScript } from './BuilderPageClientScript'

export interface BuilderPage{
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
	/**	Published : Check	*/
	published?: 0 | 1
	/**	Page Name : Data	*/
	page_name?: string
	/**	Route : Data	*/
	route?: string
	/**	Dynamic Route : Check - Map route parameters into form variables. Example <code>/profile/&lt;user&gt;</code>	*/
	dynamic_route?: 0 | 1
	/**	Is Template : Check	*/
	is_template?: 0 | 1
	/**	Template Name : Data	*/
	template_name?: string
	/**	Blocks : JSON	*/
	blocks?: any
	/**	Draft Blocks : JSON	*/
	draft_blocks?: any
	/**	Page Preview : Attach Image	*/
	preview?: string
	/**	Page Data Script : Code - data.events = frappe.get_list("Event")
<br>
<b>Note:</b> Each key value of data should be a list.	*/
	page_data_script?: string
	/**	Client Scripts : Table MultiSelect - Builder Page Client Script	*/
	client_scripts?: BuilderPageClientScript[]
	/**	Title : Data	*/
	page_title?: string
	/**	Description : Small Text	*/
	meta_description?: string
	/**	Image : Attach Image	*/
	meta_image?: string
}