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

### Motivation

Most existing solutions were either too complex, too restrictive, or difficult to integrate with the Frappe ecosystem. Additionally, pages built with these tools were often bloated with unnecessary scripts and styles. I wanted to take a stab at solving this problem while prioritising performance from day one. I aimed to address two major issues with this project: providing an intuitive way to design a web page and enabling one-click publishing. As a web developer, it helps me scratch my own itch, and I hope it helps others too.

### Key Features

- **Intuitive Visual Builder:** Simplify your workflow with a Figma-like editor.
- **Responsive Views:** Ensure your sites look great on any device without the fuss.
- **Frappe CMS Integration:** Easily fetch data from your database and create dynamic pages.
- **Scripting Capabilities:** Customize with client scripts, global scripts, and styles.
- **One-Click Publishing:** Instantly share your creation with the world in a single click.
- **Performance Excellence:** Frappe Builder does not bloat web pages with unnecessary scripts hence pages built with Frappe Builder are highly performant, consistently scoring high on Google Lighthouse tests.

## Getting Started (Production)

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
wget https://frappe.io/easy-install.py
```

**Step 2**: Run the deployment command

```bash
python3 ./easy-install.py deploy \
    --project=builder_prod_setup \
    --email=email@example.com \
    --image=ghcr.io/frappe/builder \
    --version=stable \
    --app=builder \
    --sitename subdomain.domain.tld
```

Replace the following parameters with your values:
- `email@example.com`: Your email address
- `subdomain.domain.tld`: Your domain name where Builder will be hosted

The script will set up a production-ready instance of Frappe Builder with all the necessary configurations in about 5 minutes.

## Getting Started (Development)

### Local Setup

1. [Setup Bench](https://docs.frappe.io/framework/user/en/installation).
1. In the frappe-bench directory, run `bench start` and keep it running.
1. Open a new terminal session and cd into `frappe-bench` directory and run following commands:
    ```sh
    $ bench get-app builder
    $ bench new-site sitename.localhost --install-app builder
    $ bench browse sitename.localhost --user Administrator
    ```
1. Access the builder page at `sitename.localhost:8000/builder` in your web browser.

### Github Codespaces

<!-- [Video Reference](https://github.com/frappe/builder/assets/13928957/c96ce2ce-9eb3-4bd5-8e92-0b39d971cb00) -->

1. Open [this link](https://github.com/codespaces/new?hide_repo_select=true&ref=master&repo=587413812&skip_quickstart=true&machine=standardLinux32gb&devcontainer_path=.devcontainer%2Fdevcontainer.json&geo=SoutheastAsia) and click on "Create Codespace".
2. Wait for initialization (~15 mins).
3. Run `bench start` from the terminal tab.
4. Click on the link beside "8000" port under "Ports" tab.
5. Log in with "Administrator" as the username and "admin" as the password.
6. Go to `<random-id>.github.dev/builder` to access the builder interface.

**For Frontend Development**
1. Open a new terminal session and cd into `frappe-bench/apps/builder`, and run the following commands:
    ```
    yarn install
    yarn dev
    ```
1. Now, you can access the site on vite dev server at `http://sitename.localhost:8080`

**Note:** You'll find all the code related to Builder's frontend inside `frappe-bench/apps/builder/frontend`

### Under the hood

- [Frappe Framework](https://github.com/frappe/frappe): A full-stack web application framework written in Python and Javascript. The framework provides a robust foundation for building web applications, including a database abstraction layer, user authentication, and a REST API.
- [Frappe UI](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface. The Frappe UI library provides a variety of components that can be used to build single-page applications on top of the Frappe Framework.


### Links

- [Telegram Public Group](https://t.me/frappebuilder)
- [Discuss Forum](https://discuss.frappe.io/c/frappe-builder/83)
- [Documentation](https://docs.frappe.io/builder)
- [Figma Plugin (Beta)](https://www.figma.com/community/plugin/1417835732014419099/figma-to-frappe-builder)

<br>
<hr>

<div align="center">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
