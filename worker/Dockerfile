FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
ENV DATABASE_URL=postgresql+psycopg2://campusops:campusops@db:5432/campusops
CMD ["python", "-m", "backend.app.jobs.worker"]
