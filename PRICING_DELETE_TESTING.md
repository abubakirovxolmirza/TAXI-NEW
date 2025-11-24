# 🧪 Тестирование функционала удаления прайсинга

## Шаг 1: Проверка текущих записей

### Через API
```bash
curl -X GET "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Через скрипт
```bash
python scripts\delete_pricing.py
# Выбрать опцию 1: List all pricing records
```

---

## Шаг 2: Тестирование удаления по ID

### Через API
```bash
# Предположим, есть запись с ID = 1
curl -X DELETE "http://localhost:8000/api/admin/pricing/1" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Ожидаемый результат:**
```json
{
  "success": true,
  "message": "Pricing with ID 1 deleted successfully"
}
```

### Через скрипт
```bash
python scripts\delete_pricing.py
# Выбрать опцию 2: Delete pricing by ID
# Ввести ID записи
# Подтвердить удаление
```

---

## Шаг 3: Тестирование удаления по типу сервиса

### Через скрипт
```bash
python scripts\delete_pricing.py
# Выбрать опцию 3: Delete pricing by service type
# Выбрать тип: 1 (taxi) или 2 (delivery)
# Подтвердить удаление
```

---

## Шаг 4: Тестирование удаления неактивных

### Через скрипт
```bash
python scripts\delete_pricing.py
# Выбрать опцию 4: Delete all inactive pricing
# Подтвердить удаление
```

---

## Шаг 5: Тестирование удаления всех записей

### Через API (требуется SUPERADMIN)
```bash
curl -X DELETE "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN"
```

**Ожидаемый результат:**
```json
{
  "success": true,
  "message": "All pricing deleted successfully. Total deleted: 15"
}
```

### Через быстрый скрипт
```bash
python scripts\delete_all_pricing.py
# Ввести: yes
# Ввести: DELETE ALL
```

### Через интерактивный скрипт
```bash
python scripts\delete_pricing.py
# Выбрать опцию 5: Delete ALL pricing records
# Ввести: yes
# Ввести: DELETE ALL
```

---

## Проверка ошибок

### Тест 1: Попытка удалить несуществующую запись
```bash
curl -X DELETE "http://localhost:8000/api/admin/pricing/99999" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Ожидаемый результат:**
```json
{
  "detail": "Pricing not found"
}
```
**Статус код:** 404

---

### Тест 2: Попытка удалить все записи без прав SUPERADMIN
```bash
curl -X DELETE "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Ожидаемый результат:**
```json
{
  "detail": "Superadmin access required"
}
```
**Статус код:** 403

---

## Полный тестовый сценарий

```bash
# 1. Проверить текущее состояние
curl -X GET "http://localhost:8000/api/admin/pricing" -H "Authorization: Bearer TOKEN"

# 2. Создать тестовую запись (если нужно)
curl -X POST "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_region_id": 1,
    "to_region_id": 2,
    "service_type": "taxi",
    "base_price": 50000,
    "discount_1_passenger": 0,
    "discount_2_passengers": 10,
    "discount_3_passengers": 20,
    "discount_full_car": 30
  }'

# 3. Удалить созданную запись
curl -X DELETE "http://localhost:8000/api/admin/pricing/{ID}" \
  -H "Authorization: Bearer TOKEN"

# 4. Проверить, что запись удалена
curl -X GET "http://localhost:8000/api/admin/pricing" -H "Authorization: Bearer TOKEN"
```

---

## ✅ Контрольный список

- [ ] API endpoint для удаления по ID работает
- [ ] API endpoint для удаления всех записей работает (только SUPERADMIN)
- [ ] Скрипт delete_all_pricing.py работает
- [ ] Скрипт delete_pricing.py работает
- [ ] Все варианты в меню delete_pricing.py работают
- [ ] Bat-файлы запускаются на Windows
- [ ] Ошибка 404 возвращается для несуществующих записей
- [ ] Ошибка 403 возвращается при попытке удалить все без прав SUPERADMIN
- [ ] Подтверждения работают корректно
- [ ] Счетчик удаленных записей корректный

---

## 📊 Ожидаемое поведение

### Безопасность
✅ Только ADMIN+ может удалять по ID  
✅ Только SUPERADMIN может удалить все записи через API  
✅ Скрипты требуют явного подтверждения  
✅ Двойное подтверждение для опасных операций  

### Функциональность
✅ Удаление по ID удаляет только одну запись  
✅ Удаление всех удаляет все записи  
✅ Удаление по типу удаляет только записи этого типа  
✅ Удаление неактивных не трогает активные  

### Обратная связь
✅ Показывается количество удаленных записей  
✅ Четкие сообщения об ошибках  
✅ Информативные подтверждения  

---

## 🐛 Устранение проблем при тестировании

### База данных не найдена
```bash
# Убедитесь, что БД создана
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### Модули не найдены
```bash
# Установите зависимости
pip install -r requirements.txt
```

### Нет прав доступа
```bash
# Создайте superadmin пользователя
python scripts\create_superadmin.py
```

---

Удачного тестирования! 🚀
