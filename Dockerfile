FROM python:3.11-slim-bullseye

WORKDIR /extract

COPY . .

RUN apt-get update && apt-get install -y libzbar0 python3-opencv nano \
    && pip install -r requirements.txt \
    && /extract/run_pytest.sh

WORKDIR /files

ENTRYPOINT ["python", "/extract/extract_otp_secret_keys.py"]

LABEL org.opencontainers.image.source https://github.com/scito/extract_otp_secret_keys
