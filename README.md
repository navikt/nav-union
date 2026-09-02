# nav-union
Bibliotek for å forenkle oppsett av Union tasks og abstrahere bort Nav-spesifikk konfigurasjon for image config.

## Eksempel på bruk
```python
import flyte
from nav_union.utils import default_image

image = default_image()
image = image.with_uv_project(pyproject_file="pyproject.toml")
image = image.with_env_vars({"test": "test"})

env = flyte.TaskEnvironment(
  name="my_env",
  image=image,
  ...
)
```

## Ny release

Lag og push en ny versjonstag på formen `0.2.0`:

```bash
git tag 0.2.0
git push origin 0.2.0
```

Tag-pushen oppretter en GitHub Release med automatisk genererte release notes og publiserer pakken til PyPI.
