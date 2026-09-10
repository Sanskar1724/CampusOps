FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY scripts/ ./scripts/
ENV DATABASE_URL=postgresql+psycopg2://campusops:campusops@db:5432/campusops
EXPOSE 8000
CMD ["sh", "-c", "python -m scripts.init_db && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
