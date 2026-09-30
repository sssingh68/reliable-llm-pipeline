# 1. Base image — ek ready-made Linux jisme Python pehle se laga hai
FROM python:3.11-slim

# 2. Container ke andar kaam karne ki jagah set karo
WORKDIR /app

# 3. Apna code container ke andar copy karo
COPY pipeline.py .

# 4. Jab container chale, ye command chalao
CMD ["python", "pipeline.py"]