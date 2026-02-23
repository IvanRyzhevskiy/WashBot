from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()

class SubscriptionStates(StatesGroup):
    choosing = State()
    waiting_payment = State()
