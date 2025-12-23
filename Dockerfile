FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p temp output logs

ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/app/temp
ENV OUTPUT_DIR=/app/output

CMD ["python", "bot.py"]
