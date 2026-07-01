# Release process

## Update e-footprint version in [pyproject.toml](pyproject.toml) and [version.py](efootprint/version.py)
You might need to update the version in the reference integration test json files as well.

## Update poetry dependencies

```shell
poetry update
```

## Generate latest requirements files with poetry

if not already done, install the export plugin:
```shell
poetry self add poetry-plugin-export
```

```shell
poetry export -f requirements.txt --without-hashes -o requirements.txt 
poetry export -f requirements.txt --without-hashes --only dev -o requirements-dev.txt 
```

## Make sure all tests pass

```shell
export PYTHONPATH="./:$PYTHONPATH"
python -m pytest --cov=tests
```

## Update [CHANGELOG.md](CHANGELOG.md)

## Update [README.md](README.md) if needed

## Update [tutorial notebook](tutorial.ipynb) if needed and update doc

```shell
python -m docs_sources.doc_utils.main
```

(Module mode puts the repo root on `sys.path`, so the local `efootprint` is imported even if the venv's editable install points elsewhere.)

## Check locally that new doc version is correct (changelog has been updated, tutorial and builders notebooks have been updated, etc.)

```shell
mkdocs serve
```

## Make new version commit, starting with [Vx.y.z]

## Make PR and wait for CI to pass and review

## Merge main with new version commit, and publish package

```shell
poetry publish --build
```

## Release new version of doc

```shell
mkdocs gh-deploy
```

## Publish the Docker image

Create a GitHub release tagged to match the version just published to PyPI (e.g. `v22.3.0`). Publishing
the release triggers the [`docker-publish.yml`](.github/workflows/docker-publish.yml) workflow, which
builds the [Dockerfile](Dockerfile) (installing the just-published `efootprint` from PyPI), smoke-tests
it by running a trivial model in the built image, and pushes it to Docker Hub as `boavizta/efootprint`
tagged with the release tag and `latest`.

This step requires the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets to be configured
(Settings > Secrets and variables > Actions) — provision these once, in the Boavizta org's Docker Hub
account, before the first release that should publish an image.