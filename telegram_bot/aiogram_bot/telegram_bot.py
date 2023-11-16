import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
import asyncio
import threading
from enum import Enum
from time import time

# TODO for tests

__all__ = ["async_main", "sync_main", "send_async_answer",
           "send_sync_answer", "send_query_to_queue", "start_sync_bot"]

import config



class BotWorker:
    # Scenario:
    # 1) User entered his meal request
    # 2) Service is doing his work to send the answer
    # 3) If service is doing his work too long or if it's down, bot won't get any response.
    #    If `answer_delay_sec` is passed, user can send his meal request again.
    answer_delay_sec = config.answer_delay_sec
    BOT_TOKEN = config.BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    sender = None
    LOOP = asyncio.new_event_loop()
    user_to_town_dict = dict()


def bot_init(sender_obj):
    BotWorker.sender = sender_obj


class UStates(Enum):
    AWAITING_TOWN_MESSAGE = 0
    AWAITING_USER_MEAL_REQUEST = 1
    AWAITING_SERVICE_RESPONSE = 2


class UserState(StatesGroup):
    bot_state = State()
    time_stamp = State()


# Used to query data from `BotWorker` dispatcher inner dictionary.
bot_state_key = "bot_state"
time_stamp_key = "time_stamp"


async def set_initial_state(message, state):
    await state.set_state(UserState.bot_state)
    await state.update_data(bot_state=UStates.AWAITING_TOWN_MESSAGE)
    await state.set_state(UserState.time_stamp)
    await message.answer("Привет!\nСкажи, пожалуйста, из какого ты города?")


@BotWorker.dp.message(Command("start"))
async def process_start_command(message: types.Message, state: FSMContext):
    await set_initial_state(message, state)


@BotWorker.dp.message()
async def query_message(message: types.Message, state: FSMContext):
    async def accept_town_message():
        id_user = message.from_user.id
        query = message.text

        print(f"Got town name {query}")
        BotWorker.user_to_town_dict[id_user] = query
        await state.update_data(bot_state=UStates.AWAITING_USER_MEAL_REQUEST)
        await message.answer("Теперь напиши свой запрос, пожалуйста")

    async def accept_meal_request_message():
        id_user = message.from_user.id
        query = message.text

        print(f"Got meal query {query}")
        append_task = threading.Thread(target=send_query_to_queue, args=(id_user, query, BotWorker.user_to_town_dict[id_user]))
        append_task.start()
        await state.update_data(bot_state=UStates.AWAITING_SERVICE_RESPONSE)
        await state.update_data(time_stamp=time())
        await message.answer("Твой запрос улетел на обработку! Подожди чуть-чуть.")

    data = await state.get_data()
    if bot_state_key not in data:
        await BotWorker.bot.send_message(message.from_user.id, "Что-то пошло не так.\nПоломалась машина состояний.")
        await state.set_state(UserState.bot_state)
        await state.update_data(bot_state=UStates.AWAITING_TOWN_MESSAGE)
        await state.set_state(UserState.time_stamp)
        data = await state.get_data()
        print("Retrying to get state.")

    if data[bot_state_key] == UStates.AWAITING_TOWN_MESSAGE:
        await accept_town_message()
    elif data[bot_state_key] == UStates.AWAITING_USER_MEAL_REQUEST:
        await accept_meal_request_message()
    elif data[bot_state_key] == UStates.AWAITING_SERVICE_RESPONSE:
        if time_stamp_key not in data:
            await state.set_state(UserState.time_stamp)
            await state.update_data(time_stamp=time())

        if time() - data[time_stamp_key] > BotWorker.answer_delay_sec:
            await BotWorker.bot.send_message(message.from_user.id, "Прошло достаточно много времени, начинаю обрабатывать ваш запрос!")
            await accept_meal_request_message()
        else:
            await BotWorker.bot.send_message(message.from_user.id, f"Ваш предыдуший запрос обрабатывается. Подождите "
                                                                   f"{BotWorker.answer_delay_sec - (time() - data[time_stamp_key])} секунд")
    else:
        print("We are in unknown state! Switching to the start state.")
        await set_initial_state(message, state)


def send_query_to_queue(id_user, query, town):
    BotWorker.sender.send_message(id_user, query, town)


async def send_async_answer(id_user: int, answer_body):
    text = "Вот подходящие вам варианты:\n"
    await BotWorker.bot.send_message(id_user, text)
    for res in answer_body:
        text = ""
        name = res["name"]
        address = res["address"]
        rating = str(res["rating"])
        comment = res["text"]
        geo = res["geocode"]
        text += f"{name} \n📍 {address} \t {rating}/5\n"
        text += f"{comment}\n"
        await BotWorker.bot.send_message(id_user, text)
        if geo is None:
            continue
        latitude = geo['latitude']
        longitude = geo['longitude']
        await BotWorker.bot.send_location(id_user, latitude, longitude)
    context_state = FSMContext(storage=BotWorker.dp.storage, key=StorageKey(BotWorker.bot.id, id_user, id_user))
    a = await context_state.get_data()
    await context_state.update_data(bot_state=UStates.AWAITING_USER_MEAL_REQUEST)
    await BotWorker.bot.send_message(id_user, "Можешь отправить ещё одно сообщение!")


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
    BotWorker.LOOP.create_task(send_async_answer(id_user, answer_body))


async def async_main():
    await BotWorker.dp.start_polling(BotWorker.bot)


def sync_main():
    BotWorker.LOOP.run_until_complete(async_main())


def start_sync_bot(sender):
    bot_init(sender)
    sync_main()
