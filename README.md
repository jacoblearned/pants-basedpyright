# pants-basedpyright

![PyPI - Version](https://img.shields.io/pypi/v/pants-basedpyright)
![PyPI - License](https://img.shields.io/pypi/l/pants-basedpyright)


[basedpyright](https://docs.basedpyright.com/latest/) is a fast type checker for Python, forked from [Pyright](https://github.com/microsoft/pyright).
Unlike Pyright, however, it does not depend on an active Node.js installation. This makes it simpler to integrate Pyright-compatible type checking into pure Python projects without
depending on a separate JavaScript runtime.

basedpyright also provides [several other benefits](https://docs.basedpyright.com/latest/benefits-over-pyright/better-defaults/)
like [baseline support](https://docs.basedpyright.com/latest/benefits-over-pyright/baseline/).

This repo contains a plugin for the [Pants](https://www.pantsbuild.org/) monorepo build system to integrate `basedpyright`
into Pants's type checking workflow.

Supports Pants versions **v2.27** and **v2.28**.

## Features

- Runs [basedpyright](https://docs.basedpyright.com/latest/) type checking during `$ pants check` [goal](https://www.pantsbuild.org/stable/docs/using-pants/key-concepts/goals) against appropriate Python [targets](https://www.pantsbuild.org/stable/docs/using-pants/key-concepts/targets-and-build-files).
- No dependency on Node.js, making it easier to integrate `pyright` checks into monorepos that don't want to manage Node.js environments and dependencies for Python tooling.
- Automatic [config file](https://docs.basedpyright.com/latest/configuration/config-files/) detection in the workspace root (`pyrightconfig.json` as well as the `[tool.basedpyright]` or `[tool.pyright]` sections of a `pyproject.toml` file).
- Explicit config file path support via `[basedpyright].config` section of `pants.toml` or CLI arguments , e.g. `$ pants check --basedpyright-config="path/to/config.<json|toml>" ::`.
- Supports installation from [resolves](https://www.pantsbuild.org/stable/docs/python/overview/lockfiles#getting-started-with-resolves)

## Installation

Add `pants-basedpyright` to your `plugins` list in `pants.toml`:

```toml
[GLOBAL]
plugins = [
    "pants-basedpyright==0.2.0",
]
```

Then enable the backend in your `pants.toml`:

```toml
[GLOBAL]
backend_packages = [
    # ...other backends...
    "pants_basedpyright",
]
```

## Configuration

### Config File Discovery

By default, the plugin will look for a `pyrightconfig.json` or `pyproject.toml` file in the workspace root.

A `pyproject.toml` will be considered a config file candidate if it contains a `[tool.basedpyright]` or `[tool.pyright]` section,
as `basedpyright` supports both formats for backwards compatibility with `pyright`.

If both files are present, `basedpyright` will give precedence to `pyrightconfig.json`.

### Explicit Config File Path

You can also specify a custom config file path in your `pants.toml` that will take precedence over the default discovery behavior:

```toml
[basedpyright]
config = "path/to/your/pyproject.toml"  # or "path/to/your/pyrightconfig.json"
```

Or via the CLI (taking precedence over the `pants.toml` setting, if it exists):

```bash
pants check --basedpyright-config="path/to/your/pyproject.toml" ::  # or "path/to/your/pyrightconfig.json"
```

See the [Pants options docs](https://www.pantsbuild.org/stable/docs/using-pants/key-concepts/options#setting-options) for more details on general option setting.

## Usage

Run `basedpyright` checks:

```bash
pants check ::  # Check all targets
```

## Advanced

### Installing `basedpyright` from a Resolve

[Pants resolves](https://www.pantsbuild.org/stable/docs/python/overview/lockfiles#getting-started-with-resolves) provide a mechanism to manage multiple sets of
third-party dependencies.

Using resolves, you can install a different version of `basedpyright` than the default version specified by the plugin.

It's also possible to install `basedpyright` from a resolve so the tool is version-locked alongside your other Python dependencies.
See [Lockfiles for tools](https://www.pantsbuild.org/stable/docs/python/overview/lockfiles#lockfiles-for-tools) for more details.

1. To install `basedpyright` itself from a particular [Pants Python resolve](https://www.pantsbuild.org/stable/docs/python/overview/lockfiles#getting-started-with-resolves),
first ensure resolves are enabled in your `pants.toml`:

```toml
[python]
# ...other python settings...
enable_resolves = true
default_resolve = "python-default"  # Optional, this is the default if not set

[python.resolves]
python-default = "3rdparty/python/python-default.lock"
custom-resolve-with-basedpyright = "path/to/your/custom-resolve.lock"
```

2. Run `pants generate-lockfiles` to create the lockfile if you haven't already. See [Lockfiles for tools](https://www.pantsbuild.org/stable/docs/python/overview/lockfiles#lockfiles-for-tools)
for an example `BUILD` and requirements file that `generate-lockfiles` will use to create a resolve that includes `pytest` a tool dependency.

3. Specify the resolve from which to install `basedpyright` in the `[basedpyright]` section of your `pants.toml`:

```toml
[basedpyright]
install_from_resolve = "custom-resolve-with-basedpyright"
```

Now when you run `pants check`, the plugin will use the `basedpyright` version installed from the specified resolve.

## License

MIT
