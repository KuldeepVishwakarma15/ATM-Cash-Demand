FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY Backend/requirements.txt /app/Backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/Backend/requirements.txt

COPY Backend /app/Backend
COPY Dataset/ATM_Cash_Demand.csv /app/Dataset/ATM_Cash_Demand.csv
COPY model /app/model

# Train inside the image so the model always matches the installed scikit-learn version.
RUN python /app/model/train.py > /dev/null \
    && useradd --system --uid 10001 cashcast \
    && chown -R cashcast /app
USER cashcast

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=6s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status == 200 else 1)"

CMD ["python", "-m", "uvicorn", "Backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
