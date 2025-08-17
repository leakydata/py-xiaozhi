# py-xiaozhi Documentation

This is the documentation website for the py-xiaozhi project, built with VitePress.

## Features

- Project Guide: Provides detailed instructions and development documentation for the project.
- Sponsors Page: Displays and thanks all project sponsors.
- Contribution Guide: Explains how to contribute code to the project.
- List of Contributors: Shows all developers who have contributed to the project.
- Responsive Design: Adapts to desktop and mobile devices.

## Local Development

```bash
# Install dependencies
pnpm install

# Start development server
pnpm docs:dev

# Build static files
pnpm docs:build

# Preview build results
pnpm docs:preview
```

## Directory Structure

```
documents/
├── docs/                  # Documentation source files
│   ├── .vitepress/        # VitePress configuration
│   ├── guide/             # Guide documentation
│   ├── sponsors/          # Sponsors page
│   ├── contributing.md    # Contribution guide
│   ├── contributors.md    # List of contributors
│   └── index.md           # Home page
├── package.json           # Project configuration
└── README.md              # Project description
```

## Sponsors Page

The sponsors page is implemented as follows:

1. The `/sponsors/` directory contains content related to sponsors.
2. The `data.json` file stores sponsor data.
3. Use Vue components to dynamically render the list of sponsors on the client side.
4. Provides detailed instructions and payment methods for becoming a sponsor.

## Contribution Guide

The contribution guide page provides the following content:

1. Development environment preparation guide.
2. Description of the code contribution process.
3. Coding standards and submission specifications.
4. Pull Request creation and review process.
5. Documentation contribution guide.

## List of Contributors

The list of contributors page shows all developers who have contributed to the project, including:

1. Core development team members.
2. Code contributors.
3. Documentation contributors.
4. Testers and feedback providers.

## Deployment

The documentation website is automatically deployed to GitHub Pages via GitHub Actions.