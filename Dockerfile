FROM python:3.11-slim-bullseye

WORKDIR /extract

COPY . .

RUN apt-get update && apt-get install -y libzbar0 python3-opencv \
    && pip install -r requirements.txt

WORKDIR /files

ENTRYPOINT [ "python", "/extract/extract_otp_secret_keys.py" ]
