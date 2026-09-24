declare module "webfontloader";

interface Window {
	/** Set by the server in index.html. Frappe refuses a form POST without it. */
	csrf_token: string;
}
