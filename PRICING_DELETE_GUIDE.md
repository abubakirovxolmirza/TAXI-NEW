# Удаление Прайсинга (Pricing) - Руководство

Это руководство описывает различные способы удаления записей прайсинга из базы данных.

## 📋 Содержание

1. [API Endpoints](#api-endpoints)
2. [Скрипты](#скрипты)
3. [Примеры использования](#примеры-использования)

---

## API Endpoints

### 1. Удаление прайсинга по ID

**Endpoint:** `DELETE /api/admin/pricing/{pricing_id}`

**Требования:** Роль `ADMIN` или `SUPERADMIN`

**Описание:** Удаляет конкретную запись прайсинга по её ID.

**Пример запроса:**
```bash
curl -X DELETE "http://localhost:8000/api/admin/pricing/5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Ответ:**
```json
{
  "success": true,
  "message": "Pricing with ID 5 deleted successfully"
}
```

---

### 2. Удаление всех записей прайсинга

**Endpoint:** `DELETE /api/admin/pricing`

**Требования:** Роль `SUPERADMIN` (только суперадминистратор!)

**Описание:** Удаляет ВСЕ записи прайсинга из базы данных.

**⚠️ ВНИМАНИЕ:** Это действие необратимо!

**Пример запроса:**
```bash
curl -X DELETE "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN"
```

**Ответ:**
```json
{
  "success": true,
  "message": "All pricing deleted successfully. Total deleted: 15"
}
```

---

## Скрипты

### 1. Быстрое удаление всех записей

**Файл:** `scripts/delete_all_pricing.py`

**Описание:** Простой скрипт для быстрого удаления всех записей прайсинга с двойным подтверждением.

**Запуск:**
```bash
# Windows PowerShell
python scripts/delete_all_pricing.py

# Linux/Mac
python3 scripts/delete_all_pricing.py
```

**Интерактивный процесс:**
1. Скрипт покажет количество найденных записей
2. Попросит подтверждение: введите `yes`
3. Попросит второе подтверждение: введите `DELETE ALL`
4. Удалит все записи

**Пример вывода:**
```
============================================================
DELETE ALL PRICING RECORDS
============================================================

⚠️  Found 15 pricing record(s) in database.

🔴 Are you sure you want to DELETE ALL pricing records? (yes/no): yes

🔴 This action CANNOT be undone! Type 'DELETE ALL' to confirm: DELETE ALL

✅ Successfully deleted 15 pricing record(s)!
```

---

### 2. Интерактивное удаление (с выбором критериев)

**Файл:** `scripts/delete_pricing.py`

**Описание:** Интерактивный инструмент с меню для различных вариантов удаления.

**Запуск:**
```bash
# Windows PowerShell
python scripts/delete_pricing.py

# Linux/Mac
python3 scripts/delete_pricing.py
```

**Возможности:**
1. **Просмотр всех записей** - показывает список всех прайсингов
2. **Удаление по ID** - удаляет конкретную запись
3. **Удаление по типу сервиса** - удаляет все записи для taxi или delivery
4. **Удаление неактивных** - удаляет все записи с `is_active = false`
5. **Удаление всех записей** - удаляет абсолютно все

**Пример использования:**
```
============================================================
DELETE PRICING RECORDS - INTERACTIVE TOOL
============================================================

📋 Options:
1. List all pricing records
2. Delete pricing by ID
3. Delete pricing by service type (taxi/delivery)
4. Delete all inactive pricing
5. Delete ALL pricing records
0. Exit

Select option: 1

📋 Current Pricing Records:
----------------------------------------------------------------------------------------------------
ID    From Region               To Region                 Type       Base Price   Active  
----------------------------------------------------------------------------------------------------
1     Tashkent                  Samarkand                 taxi       50000.00     Yes     
2     Tashkent                  Bukhara                   taxi       70000.00     Yes     
3     Tashkent                  Samarkand                 delivery   30000.00     Yes     
----------------------------------------------------------------------------------------------------

Total: 3 record(s)
```

---

## Примеры использования

### Пример 1: Удалить конкретный прайсинг через API

```bash
# Получить список прайсингов
curl -X GET "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Удалить прайсинг с ID = 3
curl -X DELETE "http://localhost:8000/api/admin/pricing/3" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Пример 2: Удалить все прайсинги для такси

```bash
# Запустить интерактивный скрипт
python scripts/delete_pricing.py

# Выбрать опцию 3
# Выбрать тип сервиса: taxi
# Подтвердить удаление
```

### Пример 3: Полная очистка прайсинга

**Способ 1 - Через API (нужен SUPERADMIN токен):**
```bash
curl -X DELETE "http://localhost:8000/api/admin/pricing" \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN"
```

**Способ 2 - Через скрипт:**
```bash
python scripts/delete_all_pricing.py
# Ввести: yes
# Ввести: DELETE ALL
```

**Способ 3 - Через интерактивный скрипт:**
```bash
python scripts/delete_pricing.py
# Выбрать опцию 5
# Ввести: yes
# Ввести: DELETE ALL
```

---

## ⚠️ Важные замечания

1. **Резервное копирование:** Перед массовым удалением рекомендуется сделать бэкап базы данных
2. **Права доступа:** 
   - Удаление по ID требует роль `ADMIN` или `SUPERADMIN`
   - Удаление всех записей через API требует роль `SUPERADMIN`
   - Скрипты работают напрямую с БД (используйте осторожно!)
3. **Необратимость:** Удаленные данные нельзя восстановить без бэкапа
4. **Зависимости:** Убедитесь, что удаление прайсинга не нарушит работу заказов

---

## 🔧 Устранение проблем

### Ошибка: "Pricing not found"
- Проверьте, существует ли запись с указанным ID
- Используйте endpoint `GET /api/admin/pricing` для просмотра доступных записей

### Ошибка: "Unauthorized" или "Forbidden"
- Проверьте, что вы используете валидный токен
- Убедитесь, что у вас есть необходимая роль (ADMIN или SUPERADMIN)

### Скрипт не находит модули
- Убедитесь, что вы запускаете скрипт из корневой директории проекта
- Проверьте, что все зависимости установлены: `pip install -r requirements.txt`

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь, что база данных доступна
3. Проверьте права доступа пользователя

---

**Последнее обновление:** 24 ноября 2025
