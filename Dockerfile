# =========================
# 1️⃣ Builder stage
# =========================
FROM python:3.10-alpine as builder

WORKDIR /install

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc g++ musl-dev pkgconfig python3-dev \
    freetype-dev jpeg-dev zlib-dev

COPY requirements.txt .

RUN pip install --prefix=/install/packages --no-cache-dir -r requirements.txt

# =========================
# 2️⃣ Final slim image
# =========================
FROM python:3.10-alpine

WORKDIR /app

# Install runtime libs only (not build tools)
RUN apk add --no-cache libstdc++ libjpeg libpng freetype

# Copy dependencies from builder
COPY --from=builder /install/packages /usr/local

# Copy app code
COPY . .

# Run the app
ENTRYPOINT ["python", "process_pdfs.py"]
