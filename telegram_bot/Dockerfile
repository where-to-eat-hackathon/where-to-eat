FROM docker.io/library/python:3.11-alpine

WORKDIR /telegram_bot

ENV PATH=/telegram_bot/venv/bin:$PATH
ENV PYTHONPATH=/

RUN adduser -DH bot && chown -R bot /telegram_bot
USER bot

ADD ./requirements.txt /telegram_bot/requirements.txt
RUN python -m venv venv && \
    pip install --no-cache-dir -r requirements.txt

ADD ./ /telegram_bot
CMD ["python", "main.py"]
