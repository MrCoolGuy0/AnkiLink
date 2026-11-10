FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
RUN useradd --uid 10001 --create-home relay && mkdir /data && chown relay:relay /data
USER relay
ENV HOST=0.0.0.0 PORT=8766 ANKI_LINK_DATA=/data PYTHONUNBUFFERED=1
VOLUME ["/data"]
EXPOSE 8766
CMD ["python", "server.py"]
