FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-web.txt .
COPY requirements-core.txt .
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

RUN python3 -c "\
from transformers import DonutProcessor, VisionEncoderDecoderModel; \
DonutProcessor.from_pretrained('naver-clova-ix/donut-base-finetuned-cord-v2'); \
VisionEncoderDecoderModel.from_pretrained('naver-clova-ix/donut-base-finetuned-cord-v2')"

COPY core/ ./core/
COPY web/ ./web/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "--timeout", "120", "web.app:app"]
