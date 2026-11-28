FROM python:3.11-slim

WORKDIR /app

# Upgrade pip
RUN python -m pip install --no-cache-dir --upgrade pip

# Install CPU-only PyTorch
RUN python -m pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Install project dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
