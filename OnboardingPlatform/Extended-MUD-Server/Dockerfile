FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/onboardingplatform

COPY Extended-MUD-Server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY Extended-MUD-Server ./Extended-MUD-Server
COPY shared_auth ./shared_auth

WORKDIR /opt/onboardingplatform/Extended-MUD-Server

EXPOSE 8091

CMD ["python", "MUDServer.py"]
