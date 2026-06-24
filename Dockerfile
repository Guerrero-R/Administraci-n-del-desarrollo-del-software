FROM python:3.11-slim

WORKDIR /app

ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.maxUploadSize=10"]