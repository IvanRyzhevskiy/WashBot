from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from sqlalchemy import select, and_

from core.database import get_db_context
from core.models import User, Service, Appointment, CarWash
from bot_client.states import BookingStates
from bot_client.keyboards import (
    get_services_keyboard, get_dates_keyboard, 
    get_times_keyboard, get_confirmation_keyboard
)

router = Router()

@router.message(F.text == "🚗 Записаться")
async def booking_start(message: Message, state: FSMContext):
    """Начало записи"""
    telegram_id = message.from_user.id
    
    async with get_db_context() as db:
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        
        # Сохраняем ID мойки
        await state.update_data(car_wash_id=user.car_wash_id)
        
        # Получаем услуги
        result = await db.execute(
            select(Service).where(
                Service.car_wash_id == user.car_wash_id,
                Service.is_active == True
            )
        )
        services = result.scalars().all()
        
        services_list = [{
            "id": s.id,
            "name": s.name,
            "price": s.price,
            "duration": s.duration
        } for s in services]
    
    await state.set_state(BookingStates.choosing_service)
    await message.answer(
        "Выберите услугу:",
        reply_markup=get_services_keyboard(services_list)
    )

@router.callback_query(BookingStates.choosing_service, F.data.startswith("service:"))
async def service_chosen(callback: CallbackQuery, state: FSMContext):
    """Выбор услуги"""
    service_id = int(callback.data.split(":")[1])
    await state.update_data(service_id=service_id)
    
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=get_dates_keyboard()
    )
    await callback.answer()

@router.callback_query(BookingStates.choosing_date, F.data.startswith("date:"))
async def date_chosen(callback: CallbackQuery, state: FSMContext):
    """Выбор даты"""
    date_str = callback.data.split(":")[1]
    await state.update_data(selected_date=date_str)
    
    # Получаем доступное время
    data = await state.get_data()
    service_id = data.get("service_id")
    car_wash_id = data.get("car_wash_id")
    
    async with get_db_context() as db:
        # Получаем услугу
        result = await db.execute(
            select(Service).where(Service.id == service_id)
        )
        service = result.scalar_one()
        
        # Получаем график работы
        result = await db.execute(
            select(CarWash).where(CarWash.id == car_wash_id)
        )
        carwash = result.scalar_one()
        
        # Получаем занятые слоты
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_start = datetime.combine(selected_date, datetime.min.time())
        day_end = datetime.combine(selected_date, datetime.max.time())
        
        result = await db.execute(
            select(Appointment).where(
                Appointment.car_wash_id == car_wash_id,
                Appointment.appointment_time >= day_start,
                Appointment.appointment_time <= day_end,
                Appointment.status.in_(["confirmed", "pending"])
            )
        )
        busy = result.scalars().all()
        
        # Генерируем свободные слоты
        busy_times = [a.appointment_time for a in busy]
        
        # Простая генерация слотов (для MVP)
        slots = []
        for hour in range(9, 21):  # 9:00 - 21:00
            time_str = f"{hour:02d}:00"
            slot_time = datetime.combine(selected_date, datetime.strptime(time_str, "%H:%M").time())
            
            if slot_time not in busy_times:
                slots.append(time_str)
    
    await state.set_state(BookingStates.choosing_time)
    await callback.message.edit_text(
        f"Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
        f"Выберите время:",
        reply_markup=get_times_keyboard(slots[:10])  # Ограничим 10 слотами
    )
    await callback.answer()

@router.callback_query(BookingStates.choosing_time, F.data.startswith("time:"))
async def time_chosen(callback: CallbackQuery, state: FSMContext):
    """Выбор времени"""
    time_str = callback.data.split(":")[1]
    await state.update_data(selected_time=time_str)
    
    data = await state.get_data()
    service_id = data.get("service_id")
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Service).where(Service.id == service_id)
        )
        service = result.scalar_one()
    
    selected_date = datetime.strptime(data["selected_date"], "%Y-%m-%d").date()
    selected_datetime = datetime.combine(selected_date, datetime.strptime(time_str, "%H:%M").time())
    
    await state.set_state(BookingStates.confirming)
    await callback.message.edit_text(
        f"📝 <b>Проверьте данные:</b>\n\n"
        f"Услуга: {service.name}\n"
        f"Дата: {selected_datetime.strftime('%d.%m.%Y')}\n"
        f"Время: {time_str}\n"
        f"Стоимость: {service.price}₽\n\n"
        f"Всё верно?",
        reply_markup=get_confirmation_keyboard()
    )
    await callback.answer()

@router.callback_query(BookingStates.confirming, F.data == "confirm")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение записи"""
    data = await state.get_data()
    telegram_id = callback.from_user.id
    
    service_id = data.get("service_id")
    date_str = data.get("selected_date")
    time_str = data.get("selected_time")
    
    appointment_time = datetime.strptime(
        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
    )
    
    async with get_db_context() as db:
        # Получаем пользователя
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        
        # Получаем услугу
        result = await db.execute(
            select(Service).where(Service.id == service_id)
        )
        service = result.scalar_one()
        
        # Создаем запись
        end_time = appointment_time + timedelta(minutes=service.duration)
        
        appointment = Appointment(
            user_id=user.id,
            service_id=service_id,
            car_wash_id=user.car_wash_id,
            appointment_time=appointment_time,
            end_time=end_time,
            status="confirmed"
        )
        db.add(appointment)
        await db.commit()
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"📅 {appointment_time.strftime('%d.%m.%Y в %H:%M')}\n"
        f"🚗 Услуга: {service.name}\n\n"
        f"Ждём вас!"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена записи"""
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.answer()

@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    """Назад к услугам"""
    data = await state.get_data()
    car_wash_id = data.get("car_wash_id")
    
    async with get_db_context() as db:
        result = await db.execute(
            select(Service).where(
                Service.car_wash_id == car_wash_id,
                Service.is_active == True
            )
        )
        services = result.scalars().all()
        
        services_list = [{
            "id": s.id,
            "name": s.name,
            "price": s.price,
            "duration": s.duration
        } for s in services]
    
    await state.set_state(BookingStates.choosing_service)
    await callback.message.edit_text(
        "Выберите услугу:",
        reply_markup=get_services_keyboard(services_list)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    """Назад к датам"""
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=get_dates_keyboard()
    )
    await callback.answer()
