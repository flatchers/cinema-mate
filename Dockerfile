FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependency file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

COPY src/prestart.sh /app/prestart.sh
RUN chmod +x /app/prestart.sh

ENTRYPOINT ["./prestart.sh"]
# Start Uvicorn for production
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
