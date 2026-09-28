import flyte
from pathlib import Path
import importlib.metadata

version = importlib.metadata.version("nav-union")

IMAGE_REGISTRY_BASE = "europe-west1-docker.pkg.dev/nav-data-images-prod/nav-union-images"
IMAGE_NAME = "flyte"
PYPI_PROXY_INDEX_URL = "europe-west1-python.pkg.dev/nav-data-images-prod/pypi/simple/"
CRAN_MIRROR="https://cran.uib.no"

def default_image(python_version: str = "3.14") -> flyte.Image:
    return flyte.Image.from_base(
        image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-base"
    ).clone(
        registry=IMAGE_REGISTRY_BASE,
        name=IMAGE_NAME,
        extendable=True,
        python_version=(int(python_version.split(".")[0]), int(python_version.split(".")[1]))
    ).with_env_vars({
        "UV_KEYRING_PROVIDER": "subprocess", 
        "UV_DEFAULT_INDEX": f"https://oauth2accesstoken@{PYPI_PROXY_INDEX_URL}"
    }).with_pip_packages(
        f"nav-union=={version}",
    )


def quarto_render_image(source_folder: str, pyproject_file: str, python_version: str = "3.14") -> flyte.Image:
    return flyte.Image.from_base(
        image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-quarto-base"
    ).clone(
        registry=IMAGE_REGISTRY_BASE,
        name=IMAGE_NAME,
        extendable=True,
        python_version=(int(python_version.split(".")[0]), int(python_version.split(".")[1]))
    ).with_env_vars({
        "UV_KEYRING_PROVIDER": "subprocess", 
        "UV_DEFAULT_INDEX": f"https://oauth2accesstoken@{PYPI_PROXY_INDEX_URL}"
    }).with_source_folder(
        src=Path(source_folder),
    ).with_workdir(
        workdir=source_folder.split("/")[-1],
    ).with_uv_project(
        pyproject_file=pyproject_file,
    ).with_pip_packages(
        f"nav-union=={version}",
    )

def r_image(source_folder: str, requirements_file: str="packages.R", python_version: str = "3.14") -> flyte.Image:
    return flyte.Image.from_base(
        image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-r-base"
    ).clone(
        registry=IMAGE_REGISTRY_BASE,
        name=IMAGE_NAME,
        extendable=True,
        python_version=(int(python_version.split(".")[0]), int(python_version.split(".")[1]))
    ).with_env_vars({
        "UV_KEYRING_PROVIDER": "subprocess", 
        "UV_DEFAULT_INDEX": f"https://oauth2accesstoken@{PYPI_PROXY_INDEX_URL}"
    }).with_source_folder(
        src=Path(source_folder),
    ).with_workdir(
        workdir=source_folder,
    ).with_commands(
        commands=[f"Rscript {requirements_file}"],
    ).with_pip_packages(
        f"nav-union=={version}",
    )

def find_pyproject(start_file: str) -> str:
    current = Path(start_file).resolve()

    for parent in [current.parent, *current.parents]:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        f"Could not find pyproject.toml above {start_file}"
    )


def uv_image(
    pyproject_file: str | None,
    group_name: str,
) -> flyte.Image:
    if not pyproject_file:
        pyproject_file = find_pyproject(__file__) 
    return default_image().with_uv_project(
        pyproject_file=pyproject_file,
        extra_args=f"--only-group {group_name}",
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
