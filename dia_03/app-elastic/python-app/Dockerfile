FROM python:3.11-slim

RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/app

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

EXPOSE 8080

CMD ["python", "-m", "streamlit", "run", "chat.py", "--server.port=8080", "--server.address=0.0.0.0"]
