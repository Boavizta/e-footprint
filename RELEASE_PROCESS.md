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
poetry export -f requirements.txt --without-hashes --dev -o requirements-dev.txt 
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
python docs_sources/doc_utils/main.py
```

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