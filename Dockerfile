# Minimal, toolchain-independent runner for e-footprint models.
#
# This image installs efootprint from PyPI (not from this repo's source) so it
# stays usable standalone: the pinned `pip install` here mirrors what any end
# user would get. Mount a directory containing your own script and run it:
#
#   docker run --rm -v "$PWD":/work boavizta/efootprint python /work/build_model.py
#
# EFOOTPRINT_VERSION is required (no default): the image pins the exact PyPI
# version so the pushed tag can never silently diverge from the code inside it —
# a wrong/unpublished version fails the build loudly. Build locally with e.g.
# `docker build --build-arg EFOOTPRINT_VERSION=22.2.1 .`; the release workflow
# passes the release tag (with any leading `v` stripped).
#
# No ENTRYPOINT/CMD is set: the full command (here, `python /work/build_model.py`)
# is passed straight to `docker run`, so the container just runs whatever Python
# invocation the user gives it. WORKDIR is set to /work so relative paths in a
# mounted script (e.g. writing an output HTML graph next to it) resolve where
# the user expects.
FROM python:3.12-slim

ARG EFOOTPRINT_VERSION
RUN pip install --no-cache-dir "efootprint==${EFOOTPRINT_VERSION}"

WORKDIR /work
