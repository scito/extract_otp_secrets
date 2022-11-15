FROM python:3.11-alpine

WORKDIR /extract

COPY . .

RUN pip install -r requirements.txt

WORKDIR /files

ENTRYPOINT [ "python", "/extract/extract_otp_secret_keys.py" ]
