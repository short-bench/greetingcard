FROM python:3.13-slim

RUN pip install --no-cache-dir reportlab==4.* pillow

WORKDIR /app
COPY app.py .
COPY images/ images/

# The SQLite file lives on a volume so messages survive rebuilds.
ENV CARD_DB=/data/messages.db
ENV PORT=8000
EXPOSE 8000

CMD ["python3", "app.py"]
