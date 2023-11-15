from aiogram_bot import *
import config


def start_sync_bot(sender):
    bot_init(config, sender)
    sync_main()

