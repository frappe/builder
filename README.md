<div align="center">
    <a href="https://frappe.io/products/builder">
        <img src="https://raw.githubusercontent.com/frappe/builder/master/frontend/public/builder_logo.png" height="80" alt="Frappe Builder Logo">
    </a>
    <h2>Frappe Builder</h2>
    <p>Crafting Web Pages Made Effortless!</p>

![Frappe Builder](https://github.com/frappe/builder/assets/13928957/e39f1057-4b60-4d1f-b8e9-049668738da6)
[Web page design credit](https://www.figma.com/community/file/949266436474872912)
</div>

# Frappe Builder

Frappe Builder is a low-code website builder designed for simplicity, speed, and flexibility. Craft beautiful websites effortlessly with intuitive visual builder and modern design principles. Whether you're a designer looking for ease or a developer seeking customization, Frappe Builder empowers you.

## Key Features

- **Intuitive Visual Builder:** Simplify your workflow with a Figma-like editor.
- **Responsive Views:** Ensure your sites look great on any device without the fuss.
- **Frappe CMS Integration:** Easily fetch data from your database and create dynamic pages.
- **Scripting Capabilities:** Customize with client scripts, global scripts, and styles.
- **Efficient Workflow:** Use subtle shortcuts like image dropping and streamlined page copying and more to efficiently develop pages.
- **One-Click Publishing:** Instantly share your creations with the world in a single click.
- **Performance Excellence:** Frappe Builder does not bloat web pages with unnecessary scripts hence pages built with Frappe Builder are highly performant, consistently scoring high on Google Lighthouse tests.

## Getting Started

### Managed Hosting

Get started with your personal or business site with a few clicks on [Frappe Cloud](https://frappecloud.com/marketplace/apps/builder).

### Self-hosting

If you prefer self-hosting, follow the official [Frappe Bench Installation](https://github.com/frappe/bench#installation) instructions.

## Want to Just Try Out or Contribute?

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
