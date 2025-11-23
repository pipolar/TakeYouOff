FROM python:3.12-slim
WORKDIR /app

# Install basic deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
	pip install --no-cache-dir -r /app/requirements.txt

# Ensure logs are unbuffered (helpful when running in Docker)
ENV PYTHONUNBUFFERED=1

# Copy service
COPY app.py /app/app.py

EXPOSE 6000

ENV PORT=6000
CMD ["python", "app.py"]
