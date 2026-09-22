# bullseye ships glibc 2.31, which creates threads with clone() rather than
# clone3(). Newer base images use clone3(), which the default seccomp profile of
# Docker < 20.10.10 blocks -- that breaks threads ("can't start new thread").
# Upgrade Docker on the host and this can move back to python:3.13-slim.
FROM python:3.11-slim-bullseye

# --progress-bar off keeps pip from spawning a progress-bar thread during build.
RUN pip install --no-cache-dir --progress-bar off --no-input \
        "reportlab==4.*" pillow

WORKDIR /app
COPY app.py .
COPY images/ images/

# The SQLite file lives on a volume so messages survive rebuilds.
ENV CARD_DB=/data/messages.db
ENV PORT=8000
EXPOSE 8000

CMD ["python3", "app.py"]
