FROM condaforge/mambaforge:23.1.0-4 AS build

COPY environment_deploy.yaml environment.yaml

RUN --mount=type=secret,id=CI_JOB_TOKEN \
    export CI_JOB_TOKEN=$(cat /run/secrets/CI_JOB_TOKEN) && \
    mamba env create -f environment.yaml && \
    mamba install -c conda-forge conda-pack && \
    conda-pack -f --ignore-missing-files -n ca-ghg-emission-from-lulc-change -o /tmp/env.tar && \
    mkdir /venv && \
    cd /venv && \
    tar xf /tmp/env.tar && \
    rm /tmp/env.tar  && \
    /venv/bin/conda-unpack && \
    mamba clean --all --yes

FROM python:3.11.5-bookworm as runtime

WORKDIR /ca-ghg-emission-from-lulc-change
COPY --from=build /venv /ca-ghg-emission-from-lulc-change/venv

COPY ghg_lulc ghg_lulc
COPY resources resources

ENV PYTHONPATH "${PYTHONPATH}:/ca-ghg-emission-from-lulc-change/ghg_lulc"

SHELL ["/bin/bash", "-c"]
ENTRYPOINT source /ca-ghg-emission-from-lulc-change/venv/bin/activate && \
           python ghg_lulc/plugin.py
