# __LABEL__

__DESCRIPTION__

This extension is registered as `__PUBLISHER__/__EXTENSION_SLUG__`. It adds a
right-side toolbar button that opens a live view of the Builder editor context.
Select one writable block to add the Builder icon as its last child.

## Develop

Install the dependencies:

~~~sh
npm install
~~~

Commit the generated `package-lock.json`. The release workflow uses it for
repeatable installs.

Start the development server:

~~~sh
npm run dev
~~~

Open Builder at the URL configured in `vite.config.ts`. Choose **Load development
extension**, then paste the development extension URL printed by Vite.

## Build and package

~~~sh
npm run build
npm run package -- --tag v1.0.0
~~~

The package command writes `release/__PUBLISHER__-__EXTENSION_SLUG__-1.0.0.builderext`.
The release directory is generated and is not committed.

## Publish

The manifest starts at version `1.0.0`. A release tag must be exactly the
manifest version with a `v` prefix.

You can publish either way:

1. Push a tag:

   ~~~sh
   git tag v1.0.0
   git push origin v1.0.0
   ~~~

2. Create a GitHub release in the repository UI with tag `v1.0.0`.

The included release workflow builds the extension and attaches the
`.builderext` package. It refuses to replace an existing release asset.

For the next release, update the version in both `manifest.json` and
`package.json`, commit the change, and publish the matching tag.

## License

MIT. Copyright (c) __COPYRIGHT_HOLDER__.
