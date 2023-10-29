# Frappe Builder

Crafting Web Pages Made Effortless!

> **Warning**
>
> Frappe Builder is currently in an experimental stage, and the core design might get updated to enhance app architecture as needed.


> **Note:** Builder is optimized for mac devices as of now.

<img width="1552" alt="Screenshot 2023-09-05 at 8 10 58 AM" src="https://github.com/frappe/builder/assets/13928957/da873bf4-30d5-4304-97da-7cb22901acc0">

Credit: [Web Page design source](https://www.figma.com/community/file/949266436474872912)


## Getting Started

### Using codespaces

https://github.com/frappe/builder/assets/13928957/c96ce2ce-9eb3-4bd5-8e92-0b39d971cb00

- [Open this link](https://github.com/codespaces/new?hide_repo_select=true&ref=master&repo=587413812&skip_quickstart=true&machine=standardLinux32gb&devcontainer_path=.devcontainer%2Fdevcontainer.json&geo=SoutheastAsia) and click on "Create codespace".
- Once the codespaces is created it'll take **some time** (~15mins) to initialize. You can track the progress by selecting the **Codespaces : View Creation Log** from the command palette. You will have to wait until this process is completed.
- Once the setup is done, run `bench start` command from terminal tab.
- After that, click on the link beside "8000" port under "Ports" tab.
- You'll be greeted with a login page. Enter "Administrator" in username and "admin" in password to login.
- Go to `<random-id>.github.dev/builder` to access the builder interface.




### Local setup

1. [Install bench](https://github.com/frappe/bench).
2. Install Frappe Builder app
	```sh
	$ bench get-app builder
	```
3. Create a site with builder app
	```sh
	$ bench --site sitename.localhost install-app builder
	```
4. Once the site is setup, use bench browse command to open the site in browser
	```sh
	$ bench browse sitename.localhost --user Administrator
	```
5. To access the builder page, simply enter `sitename.localhost:8000/builder` in your web browser's address bar. You will now be directed to the builder landing page.


#### License

[GNU Affero General Public License v3.0](LICENSE)
