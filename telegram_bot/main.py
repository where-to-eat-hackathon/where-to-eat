from rabbitmq_tools import get_sender, run_listener
from aiogram_bot.telegram_bot import start_sync_bot, send_sync_answer
import threading
from time import sleep


def main():
    sender = get_sender()
    mq_util_task = threading.Thread(target=run_listener,
                                    args=(send_sync_answer,))
    mq_util_task.start()
    sleep(3)
    try:
        start_sync_bot(sender)
    except KeyboardInterrupt:
        print('prepare to end')
        sender.close_connection()
        print('ready to finish')


if __name__ == '__main__':
    main()
