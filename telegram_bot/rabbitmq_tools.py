import config
import sys
from rabbitmq import RMQListener, RMQSender, defaultCallback


def run_listener(bot_gateway=defaultCallback):

    rmq_listener = RMQListener(
        queue=config.rmq_place_suggestion_queue,
        host=config.rmq_host,
        port=config.rmq_port,
        user=config.rmq_user,
        password=config.rmq_password,
        callback=bot_gateway,
    )

    try:
        rmq_listener.listen()
    except KeyboardInterrupt:
        sys.exit(0)


def get_sender():
    rmq_sender = RMQSender(
        queue=config.rmq_place_description_queue,
        host=config.rmq_host,
        port=config.rmq_port,
        user=config.rmq_user,
        password=config.rmq_password,
    )
    return rmq_sender