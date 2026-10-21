/**
 * frappe-ui's whole data layer, over the port.
 *
 * A frame runs at an opaque origin with no cookie, so a request it sends reaches
 * Frappe as Guest. frappe-ui sends through three paths — the resource fetcher,
 * `call()`, and the `use*` composables — and all three end at the global `fetch`,
 * read at request time. Wrapping `fetch` covers every one of them, and any
 * frappe-ui API added later, with no `setConfig`.
 *
 * **This is an adapter, not a gate.** It sends the request unread. The host
 * decides which operation it is, and the server checks the permission. A frame that
 * removed this wrapper would lose frappe-ui, not a check.
 */

import { ChannelCallError } from "../shared/transport/createPortChannel";
import type { ApiAnswer, ApiRequest } from "../shared/types";
import { HOST_ORIGIN, getChannel } from "./connect";

const API_PATH = /^\/api\/(method|v2)\//;

/** Frappe's own status and exception name for each refusal, so frappe-ui reads it as Frappe's. */
const REFUSALS: Record<string, [number, string]> = {
	permission_required: [403, "PermissionError"],
	read_only: [403, "PermissionError"],
	rate_limited: [429, "RateLimitExceededError"],
	unsupported_request: [404, "DoesNotExistError"],
};

const VALIDATION_ERROR: [number, string] = [417, "ValidationError"];

const urlOf = (input: RequestInfo | URL) =>
	new URL(input instanceof Request ? input.url : String(input), globalThis.location?.href);

const isApiRequest = (url: URL) => url.origin === HOST_ORIGIN && API_PATH.test(url.pathname);

const isVersion2 = (url: URL) => url.pathname.startsWith("/api/v2/");

const readBody = async (request: Request) => {
	if (request.method === "GET" || request.method === "HEAD") return undefined;
	return (await request.text()) || undefined;
};

const respond = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const answerBody = (url: URL, { data, hasNextPage, docs }: ApiAnswer) =>
	isVersion2(url) ? { data, has_next_page: hasNextPage, docs } : { message: data, docs };

/** v1 carries `exc_type` beside the message. v2 carries a list of errors. */
const refusalBody = (url: URL, type: string, message: string) =>
	isVersion2(url) ? { errors: [{ type, message, title: type }] } : { exc_type: type, message };

const refuse = (url: URL, error: unknown) => {
	const code = (error as ChannelCallError).code ?? "";
	const [status, type] = REFUSALS[code] ?? VALIDATION_ERROR;
	return respond(status, refusalBody(url, type, (error as Error).message));
};

const send = async (request: Request, url: URL) => {
	const sent: ApiRequest = {
		method: request.method,
		url: url.pathname + url.search,
		body: await readBody(request),
	};
	try {
		return respond(200, answerBody(url, await getChannel().call<ApiAnswer>("data.request", sent)));
	} catch (error) {
		return refuse(url, error);
	}
};

/** Every other URL goes out as it came: an extension may still fetch a public API of its own. */
export const installFetchBridge = () => {
	const sendOnward = globalThis.fetch.bind(globalThis);
	globalThis.fetch = (input, init) => {
		const url = urlOf(input);
		if (!isApiRequest(url)) return sendOnward(input, init);
		const request = input instanceof Request ? new Request(input, init) : new Request(url, init);
		return send(request, url);
	};
};
