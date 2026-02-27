from aiogram.fsm.state import State, StatesGroup


class TariffStates(StatesGroup):
    name = State()
    description = State()
    price = State()
    duration = State()
    car_category = State()
    max_discount = State()
