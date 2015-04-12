## Open Context Design

This directory is a node.js environment for browser-based-design environment.

This is a sub-project of the [Open Context python](https://github.com/ekansa/open-context-py) project intended to create static HTML for reference and reuse.

## Installation

Read the Makefile and run `make setup` to install dependencies.

Read package.json to understand which dependencies will be installed with <a href="https://github.com/ekansa/open-context-py">NPM</a>.

Read the gulpfile to see which commands are available.

## How to use it

- Install the dependencies.
- Run `gulp`.
- A browser and terminal process will open.
- Edit the Sass and files in the `src` directory.
- The gulp server will see the change; you should see the log change in the terminal.
- The browser page should reflect the changes almost immediately, without refreshing.
