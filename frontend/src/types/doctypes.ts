interface DocType {
    name: string;
    creation: string;
    modified: string;
    owner: string;
    modified_by: string;
  }

  interface ChildDocType extends DocType {
    parent?: string;
    parentfield?: string;
    parenttype?: string;
    idx?: number;
  }
  
// Last updated: 2026-06-05 16:00:00.000000
export interface BuilderSettings extends DocType {
  /** Script: Code */
  script?: string;
  /** Style: Code */
  style?: string;
  /** Script Public URL: Read Only */
  script_public_url?: string;
  /** Style Public URL: Read Only */
  style_public_url?: string;
  /** Favicon: Attach Image */
  favicon?: string;
  /** Home Page: Data */
  home_page?: string;
  /** Auto convert images to WebP: Check */
  auto_convert_images_to_webp: 0 | 1;
  /** Disable Auto Dark Mode: Check */
  disable_auto_dark_mode: 0 | 1;
  /** Default Language: Data */
  default_language?: string;
  /** Head HTML: Code */
  head_html?: string;
  /** Body HTML: Code */
  body_html?: string;
  /** Execute Block Scripts in Editor: Select */
  execute_block_scripts_in_editor?: 'Don\'t Execute' | 'Restricted' | 'Unrestricted';
  /** Restrict Click Handlers: Check */
  restrict_click_handlers: 0 | 1;
  /** AI API Key: Password */
  ai_api_key?: string;
}

// Last updated: 2024-11-13 20:08:24.187664
export interface UserFont extends DocType {
	/** Font Name: Data */
	font_name?: string;
	/** Font File: Attach */
	font_file?: any;
}

// Last updated: 2026-05-24 12:00:00.000000
export interface BuilderToken extends DocType {
  /** Type: Select */
  type?: 'Color' | 'Dimension';
  /** Value: Data */
  value: string;
  /** Variable Name: Data */
  token_name: string;
  /** Is Standard: Check */
  is_standard: 0 | 1;
  /** Dark Value: Data */
  dark_value?: string;
  /** Group: Data */
  group?: string;
}

// Last updated: 2026-07-01 12:00:00.000000
export interface BuilderProjectFolder extends DocType {
  /** Folder Name: Data */
  folder_name?: string;
  /** Is Standard: Check */
  is_standard: 0 | 1;
  /** Is AI Site: Check */
  is_ai_site: 0 | 1;
  /** Generation Status: Select */
  generation_status?: '' | 'Draft' | 'Generating' | 'Ready' | 'Published' | 'Failed';
  /** Active Batch ID: Data */
  active_batch_id?: string;
  /** Site Brief: Small Text */
  site_brief?: string;
  /** Home Page Route: Data */
  home_page?: string;
  /** Font Pairing: Data */
  font_pairing?: string;
  /** Header Component: Link (Builder Component) */
  header_component?: string;
  /** Footer Component: Link (Builder Component) */
  footer_component?: string;
  /** Site Spec (JSON): Long Text */
  site_spec_json?: any;
  /** Nav (JSON): Long Text */
  nav_json?: any;
}

// Last updated: 2024-09-19 13:07:00.935349
export interface BlockTemplate extends DocType {
  /** Template Name: Data */
  template_name: string;
  /** Block: JSON */
  block: any;
  /** Preview: Data */
  preview: string;
  /** Category: Select */
  category?: 'Structure' | 'Basic' | 'Typography' | 'Basic Forms' | 'Form parts' | 'Media' | 'Advanced';
  /** Preview Width: Int */
  preview_width?: number;
  /** Preview Height: Int */
  preview_height?: number;
  /** Sort Order: Int */
  sort_order?: number;
}

// Last updated: 2023-11-21 12:47:20.938211
export interface BuilderPageClientScript extends ChildDocType {
	/** Builder Script: Link (Builder Client Script) */
	builder_script: string;
}

// Last updated: 2026-06-10 10:55:22.349246
export interface BuilderClientScript extends DocType {
  /** Script: Code */
  script: string;
  /** Script Type: Autocomplete */
  script_type: string;
  /** Public URL: Read Only */
  public_url?: string;
}

// Last updated: 2026-06-04 10:00:00.000000
export interface BuilderPage extends DocType {
  /** Page Name: Data */
  page_name?: string;
  /** Route: Data */
  route?: string;
  /** Published: Check */
  published: 0 | 1;
  /** Blocks: Long Text */
  blocks?: any;
  /** Page Preview: Data */
  preview?: string;
  /** Title: Data */
  page_title?: string;
  /** Page Data Script: Code */
  page_data_script?: string;
  /** Dynamic Route: Check */
  dynamic_route: 0 | 1;
  /** Draft Blocks: Long Text */
  draft_blocks?: any;
  /** Image: Attach Image */
  meta_image?: string;
  /** Description: Small Text */
  meta_description?: string;
  /** Canonical URL: Data */
  canonical_url?: string;
  /** Language: Data */
  language?: string;
  /** Client Scripts: Table MultiSelect (Builder Page Client Script) */
  client_scripts: BuilderPageClientScript[];
  /** Is Template: Check */
  is_template: 0 | 1;
  /** Template Group: Data */
  template_group?: string;
  /** Favicon: Attach Image */
  favicon?: string;
  /** Authenticated Access: Check */
  authenticated_access: 0 | 1;
  /** Disable Indexing: Check */
  disable_indexing: 0 | 1;
  /** Project Folder: Link (Builder Project Folder) */
  project_folder?: string;
  /** Head HTML: Code */
  head_html?: string;
  /** Body HTML: Code */
  body_html?: string;
  /** Is Standard: Check */
  is_standard: 0 | 1;
  /** App: Select */
  app?: any;
  /** Published At: Datetime */
  published_at?: string;
}

// Last updated: 2026-06-10 00:00:00.000000
export interface BuilderSnapshot extends DocType {
	/** Reference Doctype: Link (DocType) */
	reference_doctype: string;
	/** Reference Name: Data */
	reference_name: string;
	/** Snapshot Type: Data */
	snapshot_type?: string;
	/** Label: Data */
	label?: string;
	/** Data: Code (JSON) */
	data: string;
}

// Last updated: 2025-01-29 09:30:34.896956
export interface BuilderComponent extends DocType {
  /** Component Name: Data */
  component_name?: string;
  /** Block: JSON */
  block?: any;
  /** For Web Page: Link (Builder Page) */
  for_web_page?: string;
  /** Component ID: Data */
  component_id?: string;
  /** Component Data Script: Code */
  component_data_script?: string;
}
