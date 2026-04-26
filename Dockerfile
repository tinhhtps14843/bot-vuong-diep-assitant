FROM python:3.11-slim

# Cài đặt ffmpeg trực tiếp vào hệ điều hành
RUN apt-get update && apt-get install -y ffmpeg nodejs && apt-get clean

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "main.py"]