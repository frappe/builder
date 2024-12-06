<div align="center">

<a href="https://frappe.io/products/builder">
    <img src="https://raw.githubusercontent.com/frappe/builder/master/frontend/public/builder_logo.png" height="100" alt="Frappe Builder Logo">
</a>

<h1>Frappe Builder</h1>

**Crafting Web Pages Made Effortless!**


![GitHub license](https://img.shields.io/github/license/frappe/builder)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/frappe/builder)
[![codecov](https://codecov.io/github/frappe/builder/branch/develop/graph/badge.svg)](https://codecov.io/github/frappe/builder)
[![unittests](https://github.com/frappe/builder/actions/workflows/server-tests.yml/badge.svg)](https://github.com/frappe/builder/actions/workflows/server-tests.yml)

![Frappe Builder](https://github.com/user-attachments/assets/e906545e-101e-4d55-8a25-2c4f6380ea5e)
[Website](https://frappe.io/builder) - [Documentation](https://docs.frappe.io/builder)
</div>

## Frappe Builder

Frappe Builder is a low-code website builder designed for simplicity, speed, and flexibility. Craft beautiful websites effortlessly with an intuitive visual builder. Whether you're a designer looking for ease or a developer seeking customization, Frappe Builder empowers you. It also features a click-to-publish option that gives you the complete end-to-end website creation experience.

### Key Features

- **Intuitive Visual Builder:** Simplify your workflow with a Figma-like editor.
- **Responsive Views:** Ensure your sites look great on any device without the fuss.
- **Frappe CMS Integration:** Easily fetch data from your database and create dynamic pages.
- **Scripting Capabilities:** Customize with client scripts, global scripts, and styles.
- **Efficient Workflow:** Use subtle shortcuts like image dropping and streamlined page copying and more to efficiently develop pages.
- **One-Click Publishing:** Instantly share your creations with the world in a single click.
- **Performance Excellence:** Frappe Builder does not bloat web pages with unnecessary scripts hence pages built with Frappe Builder are highly performant, consistently scoring high on Google Lighthouse tests.

## Getting Started

### Managed Hosting

Get started with your personal or business site with a few clicks on Frappe Cloud - our official hosting service.
<div>
	<a href="https://frappecloud.com/builder/signup" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/try-on-fc-white.png">
			<img src="https://frappe.io/files/try-on-fc-black.png" alt="Try on Frappe Cloud" height="28" />
		</picture>
	</a>
</div>


### Self Hosting

Follow these steps to set up Frappe Builder in production:

**Step 1**: Download the easy install script

```bash
wget https://frappe.fyi/easy-install.py
```

**Step 2**: Run the deployment command

```bash
python3 ./easy-install.py deploy \
    --project=builder_prod_setup \
    --email=your_email.example.com \
    --image=ghcr.io/frappe/builder \
    --version=stable \
    --app=builder \
    --sitename subdomain.domain.tld
```

Replace the following parameters with your values:
- `your_email.example.com`: Your email address
- `subdomain.domain.tld`: Your domain name where Insights will be hosted

The script will set up a production-ready instance of Frappe Builder with all the necessary configurations in about 5 minutes.

## Want to just try out or contribute?

### Codespaces

https://github.com/frappe/builder/assets/13928957/c96ce2ce-9eb3-4bd5-8e92-0b39d971cb00

1. Open [this link](https://github.com/codespaces/new?hide_repo_select=true&ref=master&repo=587413812&skip_quickstart=true&machine=standardLinux32gb&devcontainer_path=.devcontainer%2Fdevcontainer.json&geo=SoutheastAsia) and click on "Create Codespace".
2. Wait for initialization (~15 mins).
3. Run `bench start` from the terminal tab.
4. Click on the link beside "8000" port under "Ports" tab.
5. Log in with "Administrator" as the username and "admin" as the password.
6. Go to `<random-id>.github.dev/builder` to access the builder interface.

### Local Setup

1. [Install Bench](https://github.com/frappe/bench).
2. Install Frappe Builder app:
    ```sh
    $ bench get-app builder
    ```
3. Create a site with the builder app:
    ```sh
    $ bench --site sitename.localhost install-app builder
    ```
4. Open the site in the browser:
    ```sh
    $ bench browse sitename.localhost --user Administrator
    ```
5. Access the builder page at `sitename.localhost:8000/builder` in your web browser.


## Need help?

Join our [telegram group](https://t.me/frappebuilder) for instant help.

## License

[GNU Affero General Public License v3.0](LICENSE)
