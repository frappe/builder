
export interface BuilderSettings{
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
	/**	Head HTML : Code - This will be appended at the end of the &lt;head&gt;	*/
	head_html?: string
	/**	Body HTML : Code - This will be appended at the end of the &lt;body&gt;	*/
	body_html?: string
	/**	Script : Code - Global script that will be loaded with every page built with Frappe Builder	*/
	script?: string
	/**	Script Public URL : Read Only	*/
	script_public_url?: string
	/**	Style : Code - Global style that will be loaded with every page built with Frappe Builder	*/
	style?: string
	/**	Style Public URL : Read Only	*/
	style_public_url?: string
	/**	Favicon : Attach Image - An icon file with .ico extension. Should be 16 x 16 px.<br>You can generate using <a href="https://favicon-generator.org" target="_blank">favicon-generator.org</a>	*/
	favicon?: string
	/**	Auto convert images to WebP : Check - All the images uploaded to Canvas will be auto converted to WebP for better page performance.	*/
	auto_convert_images_to_webp?: 0 | 1
	/**	Default Language : Data - Default language code for HTML lang attribute (e.g., en, es, fr, de)	*/
	default_language?: string
	/**	Home Page : Data	*/
	home_page?: string,
	/**	Execute Block Scripts in Editor : Check - Tries to best emulate how blocks will look like on the live site by executing Block Scripts.	*/
	execute_block_scripts_in_editor?: "Don't Execute" | "Restricted" | "Unrestricted"
	/**	Prevent Click Emulation : Check - Prevents click events from being emulated in the editor for blocks with Block Client Scripts.	*/
	block_click_handlers?: 0 | 1
}