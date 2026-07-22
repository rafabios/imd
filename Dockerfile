FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    ca-certificates \
    unzip \
    procps \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deno.land/install.sh | sh
ENV PATH="/root/.deno/bin:${PATH}"

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY music_downloader.py /app/music_downloader.py
COPY config.sample.yaml /app/config.yaml

ENV PYTHONUNBUFFERED=1

CMD ["python", "/app/music_downloader.py"]

