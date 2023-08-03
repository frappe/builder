export interface WebPageComponent {
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
	block?: any;
	/**	For Web Page : Link - Web Page Beta	*/
	for_web_page?: string;
}
