FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/ecovision/.cache/huggingface

WORKDIR /app

RUN addgroup --system ecovision \
    && adduser --system --ingroup ecovision --home /home/ecovision ecovision

COPY requirements-lock.txt ./
RUN python -m pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 \
        torchvision==0.28.0 \
    && python -m pip install --requirement requirements-lock.txt

COPY --chown=ecovision:ecovision alembic.ini ./
COPY --chown=ecovision:ecovision migrations ./migrations
COPY --chown=ecovision:ecovision app ./app

USER ecovision

EXPOSE 8000

CMD ["python", "-m", "app.serve"]
