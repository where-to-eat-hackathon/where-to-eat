import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from typing import List
import asyncio
import threading
from enum import Enum
from time import time

# TODO for tests

__all__ = ["async_main", "sync_main", "send_async_answer",
           "send_sync_answer", "send_query_to_queue", "start_sync_bot"]

import config


class BotConsts:
    answer_delay_sec = config.answer_delay_sec
    BOT_TOKEN = config.BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    sender = None
    LOOP = asyncio.new_event_loop()


def bot_init(sender_obj):
    BotConsts.sender = sender_obj


class UStates(Enum):
    WAITING = 0
    AVAILABLE = 1


class UserState(StatesGroup):
    income_msg = State()
    time_stamp = State()


income_st = "income_msg"
time_st = "time_stamp"


@BotConsts.dp.message(Command("start"))
async def process_start_command(message: types.Message, state: FSMContext):
    await state.set_state(UserState.income_msg)
    await state.update_data(income_msg=UStates.AVAILABLE)
    await state.set_state(UserState.time_stamp)

    await message.answer(f"Привет!\nСкажи, пожалуйста, из какого ты города? {message.text}")


@BotConsts.dp.message()
async def query_message(msg: types.Message, state: FSMContext):
    async def accept_qwery():
        id_user = msg.from_user.id
        query = msg.text
        append_task = threading.Thread(target=send_query_to_queue, args=(id_user, query,))
        append_task.start()
        await state.update_data(income_msg=UStates.WAITING)
        await state.update_data(time_stamp=time())

    data = await state.get_data()
    if income_st not in data:
        await BotConsts.bot.send_message(msg.from_user.id, "something gone wrong\nNo state for you yet")
        await state.set_state(UserState.income_msg)
        await state.update_data(income_msg=UStates.AVAILABLE)
        await state.set_state(UserState.time_stamp)
        data = await state.get_data()

    if data[income_st] == UStates.AVAILABLE:
        await accept_qwery()
    else:
        if time_st not in data:
            await state.set_state(UserState.time_stamp)
            await state.update_data(time_stamp=time())

        if time() - data[time_st] > BotConsts.answer_delay_sec:
            await BotConsts.bot.send_message(msg.from_user.id, "Your qwery got timeout\nNew qwery accepted")
            await accept_qwery()
        else:
            await BotConsts.bot.send_message(msg.from_user.id, f"wait for your previous answer or for "
                                                     f"{BotConsts.answer_delay_sec - (time() - data[time_st])} sec")


def send_query_to_queue(id_user, query):
    BotConsts.sender.send_message(id_user, query)


async def send_async_answer(id_user: int, answer_body):
    text = "Вот подходящие вам варианты:\n"
    await BotConsts.bot.send_message(id_user, text)
    for res in answer_body:
        text = ""
        name = res["name"]
        address = res["address"]
        rating = str(res["rating"])
        text += f"{name} (адресс = {address}, рейтинг = {rating})\n"
        text += f"Комментарий: {text}\n"
        text += "\n"
        await BotConsts.bot.send_message(id_user, text)
    context_state = FSMContext(storage=BotConsts.dp.storage, key=StorageKey(BotConsts.bot.id, id_user, id_user))
    a = await context_state.get_data()
    await context_state.update_data(income_msg=UStates.AVAILABLE)


def send_sync_answer(ch, method, properties, body):
    """Function called to read service responses from output queue."""
    print("Read message from the output queue")
    if properties.content_encoding is not None:
        str_result = body.decode(properties.content_encoding)
    else:
        str_result = body.decode()
    json_obj = json.loads(str_result)
    id_user = json_obj['request_id']
    answer_body = json_obj['body']
    BotConsts.LOOP.create_task(send_async_answer(id_user, answer_body))


async def async_main():
    await BotConsts.dp.start_polling(BotConsts.bot)


def sync_main():
    BotConsts.LOOP.run_until_complete(async_main())


def start_sync_bot(sender):
    bot_init(sender)
    sync_main()
