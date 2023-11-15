FROM docker.io/library/python:3.11-alpine
WORKDIR /app
ENV PATH=/app/venv/bin:$PATH

RUN adduser -DH bot && chown --recursive bot /app
USER bot

ADD ./requirements.txt /app/requirements.txt
RUN python -m venv venv && pip install --no-cache-dir -r requirements.txt

ADD ./ /app

CMD ["python", "main.py"]
