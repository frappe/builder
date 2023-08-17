
export interface WebPageBeta{
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
	/**	Page Title : Data	*/
	page_title?: string
	/**	Route : Data	*/
	route?: string
	/**	Dynamic Route : Check - Map route parameters into form variables. Example <code>/profile/&lt;user&gt;</code>	*/
	dynamic_route?: 0 | 1
	/**	Blocks : JSON	*/
	blocks?: any
	/**	Page Preview : Attach Image	*/
	preview?: string
	/**	Page Data Script : Code - data.events = frappe.get_list("Event")
<br>
<b>Note:</b> Each key value of data should be a list.	*/
	page_data_script?: string
	/**	Page Data : Code	*/
	page_data?: string
}