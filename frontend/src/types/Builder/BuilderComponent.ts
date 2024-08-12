export interface BuilderComponent {
	creation: string;
	name: string;
	modified: string;
	owner: string;
	modified_by: string;
	docstatus: 0 | 1 | 2;
	parent?: string;
	parentfield?: string;
	parenttype?: string;
	idx?: number;
	/**	Component Name : Data	*/
	component_name?: string;
	/**	Block : JSON	*/
	block: string;
	/**	For Web Page : Link - Builder Page	*/
	for_web_page?: string;
	/**	Component ID : Data	*/
	component_id?: string;
}
