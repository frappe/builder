import { createResource } from "frappe-ui";
import { ref } from "vue";
import { toast } from "vue-sonner";

const API = "builder.domain";

function getErrorMessage(e: any): string {
	const msg = Array.isArray(e?.messages) && e.messages[0];
	if (msg && typeof msg === "string") return msg.replace(/<[^>]*>/g, "").trim();
	return e?.message || "Something went wrong";
}

export function useDomains() {
	const domains = ref<any[]>([]);
	const serverIP = ref<string | null>(null);
	const loading = ref(false);

	async function fetchServerIP() {
		try {
			serverIP.value = (await createResource({ url: `${API}.get_server_ip` }).submit()) as string;
		} catch {
			// non-critical
		}
	}

	async function fetchDomains() {
		loading.value = true;
		try {
			domains.value = (await createResource({ url: `${API}.get_domains` }).submit()) as any[];
		} catch (e: any) {
			toast.error(getErrorMessage(e));
		} finally {
			loading.value = false;
		}
	}

	async function checkDNS(domain: string): Promise<{ matched: boolean; error: string }> {
		try {
			const result = (await createResource({ url: `${API}.check_dns` }).submit({ domain })) as any;
			return { matched: result?.matched ?? false, error: "" };
		} catch (e: any) {
			const msg = Array.isArray(e?.messages) && e.messages[0];
			const error = (msg && typeof msg === "string" ? msg : e?.message) || "Something went wrong";
			return { matched: false, error };
		}
	}

	async function addDomain(domain: string): Promise<boolean> {
		try {
			await createResource({ url: `${API}.add_domain` }).submit({ domain });
			toast.success(`Domain ${domain} added successfully`);
			await fetchDomains();
			return true;
		} catch (e: any) {
			toast.error(getErrorMessage(e));
			return false;
		}
	}

	async function removeDomain(domain: string) {
		await callAPI("remove_domain", domain, `${domain} removed`);
	}

	async function retryDomain(domain: string) {
		await callAPI("retry_add_domain", domain, `Retrying ${domain}`);
	}

	async function setHostName(domain: string) {
		await callAPI("set_host_name", domain, `${domain} set as primary`);
	}

	async function setRedirect(domain: string) {
		await callAPI("set_redirect", domain, `Redirect enabled for ${domain}`);
	}

	async function unsetRedirect(domain: string) {
		await callAPI("unset_redirect", domain, `Redirect disabled for ${domain}`);
	}

	async function callAPI(method: string, domain: string, successMsg: string) {
		try {
			await createResource({ url: `${API}.${method}` }).submit({ domain });
			toast.success(successMsg);
			await fetchDomains();
		} catch (e: any) {
			toast.error(getErrorMessage(e));
		}
	}

	return {
		domains,
		serverIP,
		loading,
		fetchDomains,
		fetchServerIP,
		checkDNS,
		addDomain,
		removeDomain,
		retryDomain,
		setHostName,
		setRedirect,
		unsetRedirect,
	};
}
