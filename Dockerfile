FROM python:3.11-slim-bullseye

WORKDIR /extract

COPY . .

ARG run_tests=true

RUN apt-get update && apt-get install -y libzbar0 python3-opencv nano \
    && pip install -r requirements.txt \
    && if [[ "$run_tests" == "true" ]] ; then /extract/run_pytest.sh ; else echo "Not running tests..." ; fi

WORKDIR /files

ENTRYPOINT ["python", "/extract/extract_otp_secret_keys.py"]

LABEL org.opencontainers.image.source https://github.com/scito/extract_otp_secret_keys
