FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/onboardingplatform

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

COPY Domain-Manager/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY Domain-Manager ./Domain-Manager
COPY Policy_Translator ./Policy_Translator
COPY shared_auth ./shared_auth

WORKDIR /opt/onboardingplatform/Domain-Manager

EXPOSE 4321

CMD ["python", "app.py"]
