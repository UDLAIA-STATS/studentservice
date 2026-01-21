FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq-dev gcc bash netcat-openbsd \
 && pip install --no-cache-dir -r /app/requirements.txt \
 && apt-get purge -y --auto-remove gcc \
 && rm -rf /var/lib/apt/lists/*

COPY . /app

COPY docker/entrypoint_student.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8030

# EntryPoint del contenedor API
CMD ["/app/entrypoint.sh"]
