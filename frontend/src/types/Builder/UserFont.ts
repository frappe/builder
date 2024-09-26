
export interface UserFont{
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
	/**	Font Name : Data	*/
	font_name?: string
	/**	Font File : Attach	*/
	font_file?: string
}