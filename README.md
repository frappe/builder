<div align="center">

<a href="https://frappe.io/products/builder">
    <img src="https://raw.githubusercontent.com/frappe/builder/master/frontend/public/builder_logo.png" height="80" alt="Frappe Builder Logo">
</a>


<h1>Frappe Builder</h1>

**Crafting Web Pages Made Effortless**


[![GitHub release (latest by date)](https://img.shields.io/github/v/release/frappe/builder)](https://github.com/frappe/builder/releases)
[![codecov](https://codecov.io/github/frappe/builder/branch/develop/graph/badge.svg)](https://codecov.io/github/frappe/builder)
[![unittests](https://github.com/frappe/builder/actions/workflows/server-tests.yml/badge.svg)](https://github.com/frappe/builder/actions/workflows/server-tests.yml)

<div>
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/7b013cc1-fe40-4b3c-a765-d8c3697bf81e">
        <img width="1402" alt="Frappe Builder Screenshot" src="https://github.com/user-attachments/assets/d20cec8a-9e30-4ad5-9fc0-9c136fffa916">
    </picture>
</div>

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
- **Performance Excellence:** Frappe Builder does not bloat web pages with unnecessary scripts hence pages are highly performant, consistently scoring high on Google Lighthouse tests.
- **Production Ready**: [Frappe.io](https://frappe.io) built on Frappe Builder, stands as a testament to its reliability in delivering production-ready solutions.

### Under the Hood

- [Frappe Framework](https://github.com/frappe/frappe): A full-stack web application framework.
- [Frappe UI](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface.



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

### Docker

You need Docker, docker-compose and git setup on your machine. Refer [Docker documentation](https://docs.docker.com/). After that, run following command:

**Step 1**: Setup folder and download the required files

```bash
mkdir frappe-builder && cd frappe-builder
wget -O docker-compose.yml https://raw.githubusercontent.com/frappe/builder/develop/docker/docker-compose.yml
wget -O init.sh https://raw.githubusercontent.com/frappe/builder/develop/docker/init.sh
```

**Step 2**: Run the container

```bash
docker compose up
```

Wait until the setup script creates a site and you see `Current Site set to builder.localhost` in the terminal. Once done, the site [http://builder.localhost:8000](http://builder.localhost:8000) should now be available.

**Credentials:**
Username: `Administrator`
Password: `admin`

### Local Setup

1. [Setup Bench](https://docs.frappe.io/framework/user/en/installation).
1. In the frappe-bench directory, run `bench start` and keep it running.
1. Open a new terminal session and cd into `frappe-bench` directory and run following commands:
```bash
bench get-app builder
bench new-site builder.localhost --install-app builder
bench browse builder.localhost --user Administrator
```
1. Access the builder page at `builder.localhost:8000/builder` in your web browser.

**For Frontend Development**
1. Open a new terminal session and run the following commands:
```bash
cd frappe-bench/apps/builder
yarn install
yarn dev --host
```
1. Now, you can access the site on vite dev server at `http://builder.localhost:8080`

**Note:** You'll find all the code related to Builder's frontend inside `frappe-bench/apps/builder/frontend`

<h2></h2>

### Links

- [Telegram Public Group](https://t.me/frappebuilder)
- [Discuss Forum](https://discuss.frappe.io/c/frappe-builder/83)
- [Documentation](https://docs.frappe.io/builder)
- [Figma Plugin (Beta)](https://www.figma.com/community/plugin/1417835732014419099/figma-to-frappe-builder)

<br>
<br>
<div align="center">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>
