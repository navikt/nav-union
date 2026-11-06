import flyte
from pathlib import Path
import importlib.metadata
import shlex

version = importlib.metadata.version("nav-union")

IMAGE_REGISTRY_BASE = (
    "artifacts.data.nav.no/nav-union-images"
)
IMAGE_NAME = "flyte"
PYPI_INDEX_SECRET = flyte.Secret(
    key="ak-pypi-index",
    as_env_var="UV_DEFAULT_INDEX",
)


def default_image(python_version: str = "3.14") -> flyte.Image:
    return (
        flyte.Image.from_base(
            image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-base"
        )
        .clone(
            registry=IMAGE_REGISTRY_BASE,
            name=IMAGE_NAME,
            extendable=True,
            python_version=(
                int(python_version.split(".")[0]),
                int(python_version.split(".")[1]),
            ),
        )
        .with_pip_packages(
            f"nav-union=={version}",
            secret_mounts=PYPI_INDEX_SECRET,
        )
    )


def quarto_render_image(
    source_folder: str, pyproject_file: str, python_version: str = "3.14"
) -> flyte.Image:
    return (
        flyte.Image.from_base(
            image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-quarto-base"
        )
        .clone(
            registry=IMAGE_REGISTRY_BASE,
            name=IMAGE_NAME,
            extendable=True,
            python_version=(
                int(python_version.split(".")[0]),
                int(python_version.split(".")[1]),
            ),
        )
        .with_source_folder(
            src=Path(source_folder),
        )
        .with_workdir(
            workdir=source_folder.split("/")[-1],
        )
        .with_uv_project(
            pyproject_file=pyproject_file,
            secret_mounts=PYPI_INDEX_SECRET,
        )
        .with_pip_packages(
            f"nav-union=={version}",
            secret_mounts=PYPI_INDEX_SECRET,
        )
    )


def r_image(
    source_folder: str,
    requirements_file: str = "packages.R",
    python_version: str = "3.14",
) -> flyte.Image:
    return (
        flyte.Image.from_base(
            image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-r-base-v2"
        )
        .clone(
            registry=IMAGE_REGISTRY_BASE,
            name=IMAGE_NAME,
            extendable=True,
            python_version=(
                int(python_version.split(".")[0]),
                int(python_version.split(".")[1]),
            ),
        )
        .with_source_folder(
            src=Path(source_folder),
        )
        .with_workdir(
            workdir=source_folder,
        )
        .with_commands(
            commands=[
                "R --version",
                f"R_PROFILE_USER=/etc/R/cran.profile.R Rscript {shlex.quote(requirements_file)}",
            ],
            secret_mounts=flyte.Secret(key="ak-cran-netrc", mount="/etc/flyte/secrets"),
        )
        .with_pip_packages(
            f"nav-union=={version}",
            secret_mounts=PYPI_INDEX_SECRET,
        )
    )


def find_pyproject(start_file: str) -> str:
    current = Path(start_file).resolve()

    for parent in [current.parent, *current.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(f"Could not find pyproject.toml above {start_file}")


def uv_image(
    pyproject_file: str | None,
    group_name: str,
) -> flyte.Image:
    if not pyproject_file:
        pyproject_file = find_pyproject(__file__)
    return default_image().with_uv_project(
        pyproject_file=pyproject_file,
        extra_args=f"--only-group {group_name}",
        secret_mounts=PYPI_INDEX_SECRET,
    )


def oracle_dsn(
    user: str,
    password: str,
    host: str,
    service_name: str,
    port: int = 1521,
) -> str:
    return f"{user}/{password}@{host}:{port}/{service_name}"


if __name__ == "__main__":
    print(default_image())
