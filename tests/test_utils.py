from importlib.metadata import version
from pathlib import Path
from unittest.mock import Mock

import flyte
import pytest

from nav_union import utils


REGISTRY = "europe-west1-docker.pkg.dev/nav-data-images-prod/nav-union-images"


def layer(image, name):
    # Flyte exposes the image's build configuration only through _layers.
    # Keep that dependency here rather than mocking the image builder chain.
    matches = [item for item in image._layers if type(item).__name__ == name]
    assert len(matches) == 1, f"Expected one {name} layer, found {len(matches)}"
    return matches[0]


@pytest.mark.parametrize(
    ("factory", "suffix"),
    [
        (utils.default_image, "base"),
        (utils.quarto_render_image, "quarto-base"),
        (utils.r_image, "r-base-v2"),
    ],
)
@pytest.mark.parametrize("python_version", [None, "3.12"])
def test_image_defaults_and_python_version(factory, suffix, python_version, tmp_path):
    kwargs = {}
    if factory is not utils.default_image:
        kwargs["source_folder"] = str(tmp_path)
    if factory is utils.quarto_render_image:
        kwargs["pyproject_file"] = str(tmp_path / "pyproject.toml")
    if python_version is not None:
        kwargs["python_version"] = python_version

    image = factory(**kwargs)

    expected_version = python_version or "3.14"
    assert isinstance(image, flyte.Image)
    assert image.base_image == f"{REGISTRY}/flyte:{expected_version}-{suffix}"
    assert image.registry == REGISTRY
    assert image.name == "flyte"
    assert image.extendable is True
    assert image.python_version == tuple(map(int, expected_version.split(".")))
    assert dict(layer(image, "Env").env_vars) == {
        "UV_KEYRING_PROVIDER": "subprocess",
        "UV_DEFAULT_INDEX": (
            "https://oauth2accesstoken@"
            "europe-west1-python.pkg.dev/nav-data-images-prod/pypi/simple/"
        ),
    }
    assert layer(image, "PipPackages").packages == (f"nav-union=={version('nav-union')}",)


def test_quarto_image_copies_source_and_installs_project(tmp_path):
    source = tmp_path / "reports"
    source.mkdir()
    pyproject = source / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'reports'\nversion = '0.1.0'\n")

    image = utils.quarto_render_image(str(source), str(pyproject))

    assert layer(image, "CopyConfig").src == source
    assert layer(image, "WorkDir").workdir == "reports"
    assert layer(image, "UVProject").pyproject == pyproject


@pytest.mark.parametrize(
    ("requirements_file", "expected_argument"),
    [(None, "packages.R"), ("my packages.R", "'my packages.R'")],
)
def test_r_image_configures_install_command_and_secret(
    tmp_path, requirements_file, expected_argument
):
    kwargs = {} if requirements_file is None else {"requirements_file": requirements_file}
    image = utils.r_image(str(tmp_path), **kwargs)

    assert layer(image, "CopyConfig").src == tmp_path
    assert layer(image, "WorkDir").workdir == str(tmp_path)
    commands = layer(image, "Commands")
    assert commands.commands == (
        "R --version",
        f"R_PROFILE_USER=/etc/R/cran.profile.R Rscript {expected_argument}",
    )
    assert len(commands.secret_mounts) == 1
    assert commands.secret_mounts[0].key == "ak-cran-netrc"
    assert commands.secret_mounts[0].mount == "/etc/flyte/secrets"


@pytest.mark.parametrize("levels", [0, 1, 3])
def test_find_pyproject_searches_ancestors(tmp_path, levels):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.touch()
    directory = tmp_path.joinpath(*[f"level{i}" for i in range(levels)])
    directory.mkdir(parents=True, exist_ok=True)
    start_file = directory / "task.py"
    start_file.touch()

    assert utils.find_pyproject(str(start_file)) == str(pyproject)


def test_find_pyproject_prefers_nearest_project(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    nested = tmp_path / "nested"
    nested.mkdir()
    nearest = nested / "pyproject.toml"
    nearest.touch()

    assert utils.find_pyproject(str(nested / "task.py")) == str(nearest)


def test_find_pyproject_raises_when_no_project_exists(tmp_path, monkeypatch):
    # Isolate discovery from any pyproject.toml above pytest's temp directory.
    monkeypatch.setattr(Path, "exists", lambda path: False)
    start_file = str(tmp_path / "task.py")

    with pytest.raises(FileNotFoundError) as error:
        utils.find_pyproject(start_file)

    assert str(error.value) == f"Could not find pyproject.toml above {start_file}"


def test_uv_image_uses_explicit_project_and_dependency_group(tmp_path, monkeypatch):
    find = Mock()
    monkeypatch.setattr(utils, "find_pyproject", find)
    pyproject = tmp_path / "pyproject.toml"

    image = utils.uv_image(str(pyproject), "reports")

    find.assert_not_called()
    project = layer(image, "UVProject")
    assert project.pyproject == pyproject
    assert project.extra_args == "--only-group reports"


def test_uv_image_discovers_project_when_omitted(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    find = Mock(return_value=str(pyproject))
    monkeypatch.setattr(utils, "find_pyproject", find)

    image = utils.uv_image(None, "reports")

    find.assert_called_once_with(utils.__file__)
    assert layer(image, "UVProject").pyproject == pyproject
    assert layer(image, "UVProject").extra_args == "--only-group reports"
