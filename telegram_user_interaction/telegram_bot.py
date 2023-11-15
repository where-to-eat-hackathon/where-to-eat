from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.exceptions import TelegramBadRequest
from typing import List
import asyncio
import threading
from enum import Enum
from time import time
import os

# TODO for tests
from telegram_repository import message_repo

__all__ = ["async_main", "sync_main", "send_async_answer", "send_sync_answer", "send_qwery_to_queue"]


answer_delay_sec = 12
if "ANSWER_DELAY_SEC" in os.environ:
    answer_delay_sec = int(os.getenv("ANSWER_DELAY_SEC"))

BOT_TOKEN = ""
if "BOT_TOKEN" in os.environ:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_LINK = ""
if "BOT_LINK" in os.environ:
    BOT_LINK = os.getenv("BOT_LINK")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class UStates(Enum):
    WAITING = 0
    AVAILABLE = 1


class UserState(StatesGroup):
    income_msg = State()
    time_stamp = State()


income_st = "income_msg"
time_st = "time_stamp"


@dp.message(Command("start"))
async def process_start_command(message: types.Message, state: FSMContext):
    await state.set_state(UserState.income_msg)
    await state.update_data(income_msg=UStates.AVAILABLE)
    await state.set_state(UserState.time_stamp)

    await message.answer(f"Привет!\nНапиши мне что-нибудь! {message.text}")


@dp.message(Command("ans"))
async def answer_command(message: types.Message):
    try:
        id_user = int(message.text.split()[1])
    except ValueError:
        await bot.send_message(message.from_user.id, "id not correct")
        return

    answer = ["answer is ", str(message_repo.get(id_user))]
    try:
        await send_async_answer(id_user, answer)
    except TelegramBadRequest:
        await bot.send_message(message.from_user.id, "id not correct")
        return


@dp.message()
async def qwery_message(msg: types.Message, state: FSMContext):
    async def accept_qwery():
        id_user = msg.from_user.id
        query = msg.text
        append_task = threading.Thread(target=send_qwery_to_queue, args=(id_user, query,))
        append_task.start()
        await state.update_data(income_msg=UStates.WAITING)
        await state.update_data(time_stamp=time())

    data = await state.get_data()
    if income_st not in data:
        await bot.send_message(msg.from_user.id, f"something gone wrong\nNo state for you yet")
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

        if time() - data[time_st] > answer_delay_sec:
            await bot.send_message(msg.from_user.id, "Your qwery got timeout\nNew qwery accepted")
            await accept_qwery()
        else:
            await bot.send_message(msg.from_user.id, f"wait for your previous answer or for "
                                                     f"{answer_delay_sec - (time() - data[time_st])} sec")


def send_qwery_to_queue(id_user, query):
    # TODO call rabbitmq lib funcs
    message_repo.put(id_user, query)


async def send_async_answer(id_user: int, answer: List[str]):
    text = '\n'.join(answer)
    await bot.send_message(id_user, text)
    context_state = FSMContext(storage=dp.storage, key=StorageKey(bot.id, id_user, id_user))
    a = await context_state.get_data()
    await context_state.update_data(income_msg=UStates.AVAILABLE)


def send_sync_answer(id_user: int, answer: List[str]):
    coroutine = send_async_answer(id_user, answer)
    asyncio.get_event_loop().create_task(coroutine)


async def async_main():
    await dp.start_polling(bot)


def sync_main():
    asyncio.run(async_main())


if __name__ == '__main__':
    sync_main()
