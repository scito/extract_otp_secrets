FROM python:3.11-slim-bullseye

# https://docs.docker.com/engine/reference/builder/

# For debugging
# docker build . -t extract_otp_secrets --pull --build-arg RUN_TESTS=false
# docker run --rm -v "$(pwd)":/files:ro extract_otp_secrets
# docker run --entrypoint /extract/run_pytest.sh --rm -v "$(pwd)":/files:ro extract_otp_secrets
# docker run --entrypoint /bin/bash -it --rm -v "$(pwd)":/files:ro --device="/dev/video0:/dev/video0" --env="DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix:ro extract_otp_secrets

WORKDIR /extract

COPY . .

ARG RUN_TESTS=true

RUN apt-get update && apt-get install -y \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libzbar0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -U -r \
        requirements.txt \
    && if [ "$RUN_TESTS" = "true" ]; then /extract/run_pytest.sh; else echo "Not running tests..."; fi

WORKDIR /files

ENTRYPOINT ["python", "/extract/src/extract_otp_secrets.py"]

LABEL org.opencontainers.image.source https://github.com/scito/extract_otp_secrets
LABEL org.opencontainers.image.license GPL-3.0+
