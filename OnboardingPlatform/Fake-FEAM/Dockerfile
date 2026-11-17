FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/onboardingplatform

COPY Fake-FEAM/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY Fake-FEAM ./Fake-FEAM

WORKDIR /opt/onboardingplatform/Fake-FEAM

EXPOSE 8181

ENV PORT=8181

CMD ["python", "app.py"]
