FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY evez_tools ./evez_tools
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 evez && mkdir -p /app/logs && chown -R evez:evez /app
USER evez
EXPOSE 8080
CMD ["uvicorn", "evez_tools.app:app", "--host", "0.0.0.0", "--port", "8080"]
