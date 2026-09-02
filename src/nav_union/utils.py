import flyte

IMAGE_REGISTRY_BASE = "europe-west1-docker.pkg.dev/nav-data-images-prod/nav-union-images"
IMAGE_NAME = "flyte"
PYPI_PROXY_INDEX_URL = "europe-west1-python.pkg.dev/nav-data-images-prod/pypi/simple/"

def create_default_task_env(name: str, python_version: str) -> flyte.TaskEnvironment:
    return flyte.TaskEnvironment(
            name=name,
            image=flyte.Image.from_base(
              image_uri=f"{IMAGE_REGISTRY_BASE}/{IMAGE_NAME}:{python_version}-base"
            )
            .clone(
                registry=IMAGE_REGISTRY_BASE,
                name=IMAGE_NAME,
                extendable=True,
            )
            .with_env_vars({
              "UV_KEYRING_PROVIDER": "subprocess", 
              "UV_DEFAULT_INDEX": f"https://oauth2accesstoken@{PYPI_PROXY_INDEX_URL}"
            })
    )
