/**
 *
 * This utility provides a optimized way to fetch and display user information
 * (like full name and avatar) in the UI.
 *
 * Why is it complex?
 * 1. Synchronous & Reactive: UI components can call `getUserInfo(email)` and immediately
 *    get a reactive object. They don't need to handle promises or loading states manually.
 *    The object starts with placeholder data and updates automatically when real data arrives.
 *
 * 2. Global Caching: fetched user data is stored in `usersByName` to ensure we never
 *    fetch the same user twice in the same session.
 *
 * 3. Batched Requests: If a page renders a list of 50 items, we don't want 50 API calls.
 *    This utility queues requests and sends them in a single batch (debounced by 50ms).
 *
 * 4. Request Deduplication: If multiple components request the same user simultaneously
 *    (during the debounce window), they subscribe to the same pending request.
 */
import { createResource } from "frappe-ui";
import { reactive } from "vue";

let usersByName = reactive({}) as { [key: string]: UserInfo };
const activeRequests = new Set<string>();
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
const queue = new Set<string>();

export function getUserInfo(email: string) {
	return getUsersInfo([email])[0];
}

export function getUsersInfo(emails: string[]) {
	const resultIs = [] as UserInfo[];

	emails.forEach((email) => {
		if (!usersByName[email]) {
			usersByName[email] = {
				user: email,
				fullname: email,
				image: "",
			};
		}

		if (!usersByName[email].image && !activeRequests.has(email)) {
			queue.add(email);
			triggerDebouncedFetch();
		}
		resultIs.push(usersByName[email]);
	});

	return resultIs;
}

function triggerDebouncedFetch() {
	if (debounceTimer) clearTimeout(debounceTimer);
	debounceTimer = setTimeout(processBatch, 50);
}

async function processBatch() {
	const emailsToFetch = Array.from(queue);
	if (emailsToFetch.length === 0) return;

	queue.clear();
	emailsToFetch.forEach((email) => activeRequests.add(email));
	debounceTimer = null;

	try {
		const res = (await createResource({
			method: "POST",
			url: `/api/method/frappe.desk.form.load.get_user_info_for_viewers`,
		}).submit({
			users: JSON.stringify(emailsToFetch),
		})) as { [key: string]: UserInfo };

		emailsToFetch.forEach((email) => {
			if (res && res[email]) {
				Object.assign(usersByName[email], res[email]);
			}
		});
	} catch (error) {
		console.error("Failed to fetch users info", error);
	} finally {
		emailsToFetch.forEach((email) => {
			activeRequests.delete(email);
		});
	}
}
