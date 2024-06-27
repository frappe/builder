import { createResource } from "frappe-ui";
import { reactive } from "vue";

let usersByName = reactive({}) as { [key: string]: UserInfo };

export async function getUsersInfo(emails: string[]) {
	const usersToFetch = [] as string[];
	const usersInfo = [] as UserInfo[];
	emails.forEach((email) => {
		if (!usersByName[email]) {
			usersToFetch.push(email);
		} else {
			usersInfo.push(usersByName[email]);
		}
	});
	if (usersToFetch.length) {
		await createResource({
			method: "POST",
			url: `/api/method/frappe.desk.form.load.get_user_info_for_viewers`,
		})
			.submit({
				users: JSON.stringify(usersToFetch),
			})
			.then((res: { [key: string]: UserInfo }) => {
				usersToFetch.forEach((email) => {
					usersByName[email] = res[email];
					usersInfo.push(usersByName[email]);
				});
			});
	}
	return usersInfo as UserInfo[];
}
