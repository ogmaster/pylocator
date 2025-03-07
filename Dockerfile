FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Expose the port Dash runs on
EXPOSE 8050

# Command to run the application
CMD ["python", "app.py"]