# Frappe Builder

Crafting Web Pages Made Effortless!

> **Warning**
>
> Frappe Builder is currently in an experimental stage, and the core design might get updated to enhance app architecture as needed.


> **Note:** Builder is optimized for mac devices as of now.

<img width="1552" alt="Screenshot 2023-09-05 at 8 10 58 AM" src="https://github.com/frappe/builder/assets/13928957/da873bf4-30d5-4304-97da-7cb22901acc0">

Credit: [Web Page design source](https://www.figma.com/community/file/949266436474872912)


## Getting Started

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
