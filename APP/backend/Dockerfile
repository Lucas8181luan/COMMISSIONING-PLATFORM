FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000"]
