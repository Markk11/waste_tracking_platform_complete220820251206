FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "waste_tracking_platform:app", "--bind", "0.0.0.0:8000"]
