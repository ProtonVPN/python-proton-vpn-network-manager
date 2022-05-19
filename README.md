# Proton VPN Network Manager

The `proton-vpn-network-manager` component provides the necessary functionality for other components to interact with
[NetworkManager](https://www.networkmanager.dev).

## Development

Even though our CI pipelines always test and build releases using Linux distribution packages,
you can use pip to set up your development environment.

### Proton package registry

If you didn't do it yet, to be able to pip install ProtonVPN components you'll
need to set up our internal Python package registry. You can do so running the
command below, after replacing `{GITLAB_TOKEN`} with your
[personal access token](https://gitlab.protontech.ch/help/user/profile/personal_access_tokens.md)
with the scope set to `api`.

```shell
pip config set global.index-url https://__token__:{GITLAB_TOKEN}@gitlab.protontech.ch/api/v4/groups/777/-/packages/pypi/simple
```

In the index URL above, `777` is the id of the current root GitLab group,
the one containing the repositories of all our ProtonVPN components.

### Known issues

This component depends on the `PyGObject` and `dbus-python` python packages. Unfortunately, quite a few
distribution packages are required before being able to pip install these 2 dependencies.

To be able to pip install `PyGObject`, please check the required distribution packages in the
[official documentation](https://pygobject.readthedocs.io/en/latest/devguide/dev_environ.html).

To be able to pip install `dbus-python` (version 1.2.18, at the time of writing), the following Debian
packages were required on Ubuntu 22.04. You'll need the equivalent packages in other distributions.

```shell
sudo apt install pkg-config libdbus-1-dev libglib2.0-dev
```

### Virtual environment

You can create the virtual environment and install the rest of dependencies as follows:

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Tests

You can run the tests with:

```shell
pytest
```
