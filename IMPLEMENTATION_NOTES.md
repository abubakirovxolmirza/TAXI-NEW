# Реализованные изменения в TAXI-NEW

## 1. Добавлено поле Gender для пользователей

### Изменения в моделях:
- **app/models.py**: Добавлен `Gender` enum с вариантами: `male`, `female`, `other`
- **app/models.py**: Добавлено поле `gender` к модели `User` (nullable)

### Изменения в schemas:
- **app/schemas.py**: Обновлен импорт для добавления `Gender`
- **app/schemas.py**: Добавлено `gender` поле в `UserCreate`
- **app/schemas.py**: Добавлено `gender` поле в `UserUpdate`
- **app/schemas.py**: Добавлено `gender` поле в `UserResponse` - теперь все User данные отображают gender

### Миграция:
- **alembic/versions/add_gender_seat_type_pricing.py**: Добавлена колонка `gender` в таблицу `users`

---

## 2. Добавлен новый endpoint для удаления Driver

### Изменения в routers:
- **app/routers/admin.py**: Добавлен новый DELETE endpoint `/api/admin/drivers/{driver_id}`
  - Удаляет только профиль driver
  - Оставляет associated user account нетронутым
  - Меняет роль пользователя обратно на USER
  - Отправляет уведомление пользователю о удалении driver профиля
  - Требует admin доступ

---

## 3. Добавлена функциональность выбора места в такси

### Новые enum и поля:
- **app/models.py**: Добавлен `SeatType` enum с вариантами: `front`, `back`
- **app/models.py**: Добавлено поле `seat_type` к модели `TaxiOrder` (nullable)
- **app/models.py**: Добавлены поля `front_seat_price` и `back_seat_price` к модели `Pricing`

### Изменения в schemas:
- **app/schemas.py**: Обновлен импорт для добавления `SeatType`
- **app/schemas.py**: Добавлено `seat_type` поле в `TaxiOrderCreate` (optional)
- **app/schemas.py**: Добавлено `seat_type` поле в `TaxiOrderResponse`
- **app/schemas.py**: Добавлены `front_seat_price` и `back_seat_price` в `PricingCreate`
- **app/schemas.py**: Добавлены `front_seat_price` и `back_seat_price` в `PricingUpdate`
- **app/schemas.py**: Добавлены `front_seat_price` и `back_seat_price` в `PricingResponse`

### Логика автоматического выбора места:
- **app/routers/taxi_orders.py**: Обновлен `create_taxi_order()` endpoint
  - Если клиент не выбрал место вручную (seat_type = None):
    - Для 1 пассажира: автоматически выбирается FRONT
    - Для 2+ пассажиров: автоматически выбирается BACK
  - Если клиент выбрал место вручную: используется выбранное значение
  - Место отправляется в WebSocket broadcast

### Обновления функций расчета цены:
- **app/utils.py**: Обновлена функция `calculate_taxi_price()`
  - Теперь принимает параметр `seat_type` (optional)
  - Использует `front_seat_price` если seat_type = FRONT и цена указана в pricing
  - Использует `back_seat_price` если seat_type = BACK и цена указана в pricing
  - Fallback на `base_price` если seat-specific цена не указана
  - Применяет скидки на основе числа пассажиров как раньше

### Миграция:
- **alembic/versions/add_gender_seat_type_pricing.py**: 
  - Добавлена колонка `seat_type` в таблицу `taxi_orders`
  - Добавлены колонки `front_seat_price` и `back_seat_price` в таблицу `pricing`

---

## Как использовать новые функции

### Gender:
```json
POST /api/auth/register
{
  "telephone": "99899123456",
  "name": "John Doe",
  "password": "password123",
  "confirm_password": "password123",
  "gender": "male"
}
```

### Удаление Driver:
```bash
DELETE /api/admin/drivers/{driver_id}
```

### Taxi Order с выбором места:
```json
POST /api/taxi-orders/
{
  "username": "John",
  "telephone": "99899123456",
  "from_region_id": 1,
  "from_district_id": 1,
  "to_region_id": 2,
  "to_district_id": 2,
  "passengers": 1,
  "seat_type": "front",  // Optional - если не указать, выберется автоматически
  "date": "07.12.2025",
  "time_start": "14:30",
  "time_end": "15:30"
}
```

### Pricing с разными ценами для сидений:
```json
POST /api/admin/pricing
{
  "from_region_id": 1,
  "to_region_id": 2,
  "service_type": "taxi",
  "base_price": 50000,
  "front_seat_price": 45000,
  "back_seat_price": 55000,
  "discount_1_passenger": 0,
  "discount_2_passengers": 5,
  "discount_3_passengers": 10,
  "discount_full_car": 15
}
```

---

## Миграция базы данных

Для применения всех изменений к БД:
```bash
alembic upgrade add_gender_seat_type_pricing
```

Для отката:
```bash
alembic downgrade add_system_settings
```

---

## Синтаксис и проверки

Все файлы прошли проверку на синтаксические ошибки:
- ✅ app/models.py
- ✅ app/schemas.py
- ✅ app/utils.py
- ✅ app/routers/taxi_orders.py
- ✅ app/routers/admin.py

