FROM python:3.12-slim

RUN pip install uv
RUN --mount=source=dist,target=/dist uv pip install --no-cache --system /dist/*.whl 

COPY src/frontend/app.py /app/app.py
WORKDIR /app

CMD ["sh", "-c", "streamlit run app.py --server.port $PORT --server.address 0.0.0.0"]