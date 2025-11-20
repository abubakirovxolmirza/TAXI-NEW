# Руководство по установке пароля для гостевых пользователей

## Проблема

Когда клиент создаёт заказ без регистрации (через POST-запрос без токена), система автоматически создаёт для него учётную запись с **случайным паролем**, который клиент не знает.

## Решение

Добавлен новый эндпоинт `/api/auth/set-password`, который позволяет пользователю установить пароль **используя только номер телефона** - без токена и без знания старого пароля.

---

## Сценарий использования

### Шаг 1: Клиент создаёт заказ без регистрации

```bash
POST /api/taxi-orders
Content-Type: application/json

{
  "username": "Алишер",
  "telephone": "+998901234567",
  "from_region_id": 1,
  "to_region_id": 2,
  "from_district_id": 1,
  "to_district_id": 5,
  "passengers": 2,
  "date": "2025-11-25",
  "time_start": "10:00",
  "time_end": "12:00"
}
```

**Результат:** 
- Система создаёт User с `telephone="+998901234567"` и случайным паролем
- Создаётся заказ, привязанный к этому пользователю
- Пользователь **не знает** свой пароль

---

### Шаг 2: Клиент устанавливает пароль (БЕЗ ТОКЕНА!)

Клиент просто указывает свой номер телефона и новый пароль:

```bash
POST /api/auth/set-password
Content-Type: application/json

{
  "telephone": "+998901234567",
  "new_password": "MySecurePassword123",
  "confirm_password": "MySecurePassword123"
}
```

**Ответ:**
```json
{
  "message": "Password set successfully. You can now login with your new password.",
  "telephone": "+998901234567"
}
```

✅ **Токен НЕ требуется!**  
✅ **Старый пароль НЕ требуется!**  
✅ **Только номер телефона и новый пароль!**

---

### Шаг 3: Клиент может войти с новым паролем

```bash
POST /api/auth/login
Content-Type: application/json

{
  "telephone": "+998901234567",
  "password": "MySecurePassword123"
}
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 42,
    "telephone": "+998901234567",
    "name": "Алишер",
    "role": "user",
    "language": "uz_latin",
    "is_active": true,
    "created_at": "2025-11-20T10:30:00Z"
  }
}
```

Теперь клиент может:
- ✅ Просматривать историю заказов
- ✅ Отслеживать активные заказы
- ✅ Управлять профилем
- ✅ Менять пароль через `/api/auth/change-password` (с проверкой старого пароля)

---

## Отличия между `/set-password` и `/change-password`

| Характеристика | `/set-password` | `/change-password` |
|----------------|-----------------|-------------------|
| **Требует токен** | ❌ Нет | ✅ Да |
| **Требует старый пароль** | ❌ Нет | ✅ Да |
| **Требует telephone** | ✅ Да | ❌ Нет (из токена) |
| **Для кого** | Гостевые пользователи | Зарегистрированные пользователи |
| **Валидация** | Минимум 6 символов | Минимум 6 символов + проверка старого |
| **Безопасность** | Средняя (только номер телефона) | Высокая (токен + старый пароль) |

---

## Безопасность

### ⚠️ Важно понимать!

Эндпоинт `/set-password` **НЕ требует токена**, только номер телефона. Это означает:

**Риски:**
- 🔴 Любой человек, знающий чужой номер телефона, может установить/изменить пароль
- 🔴 Нет защиты от автоматических атак (brute force)
- 🔴 Нет проверки, что это действительно владелец номера

**Рекомендации для безопасности:**

1. **Добавить rate limiting** (ограничение запросов):
   ```python
   # Не более 3 попыток установки пароля в час для одного номера
   ```

2. **Логировать все изменения пароля:**
   ```python
   # Сохранять IP, время, старый/новый пароль (хеш)
   ```

3. **Отправлять уведомления:**
   ```python
   # SMS или уведомление в приложении: "Ваш пароль был изменён"
   ```

4. **Добавить простую проверку** (опционально):
   ```python
   # Например: имя пользователя + номер телефона
   # Или: последние 4 цифры заказа
   ```

### 💡 Улучшенная версия с базовой защитой

Можно добавить дополнительную проверку - например, имя пользователя:

```python
@router.post("/set-password")
def set_password(
    password_data: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.telephone == password_data.telephone).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Дополнительная проверка: имя должно совпадать
    if password_data.username and user.name != password_data.username:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    
    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    # TODO: Отправить SMS уведомление
    # send_sms(user.telephone, "Ваш пароль был изменён")
    
    return {"message": "Password set successfully"}
```

---

## Интеграция с фронтендом

### Пример на JavaScript (React/Vue/Angular)

```javascript
// Установка пароля без токена - просто номер телефона!
async function setPassword(telephone, newPassword) {
  const response = await fetch('https://api.yourapp.com/api/auth/set-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
      // НЕТ Authorization header!
    },
    body: JSON.stringify({
      telephone: telephone,
      new_password: newPassword,
      confirm_password: newPassword
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    console.log('Password set successfully!', data);
    // Redirect to login page
    window.location.href = '/login';
  } else {
    console.error('Error:', data.detail);
  }
}

// Использование
setPassword('+998901234567', 'MyNewPassword123');
```

---

## Postman примеры

### 1. Создать заказ без токена (гостевой пользователь)
```
POST {{base_url}}/api/taxi-orders
Body (JSON):
{
  "username": "Test User",
  "telephone": "+998901234567",
  "from_region_id": 1,
  "to_region_id": 2,
  "from_district_id": 1,
  "to_district_id": 5,
  "passengers": 2,
  "is_mail_delivery": false,
  "date": "2025-11-25",
  "time_start": "10:00",
  "time_end": "12:00"
}
```

### 2. Установить пароль (БЕЗ ТОКЕНА!)
```
POST {{base_url}}/api/auth/set-password
Body (JSON):
{
  "telephone": "+998901234567",
  "new_password": "MyPassword123",
  "confirm_password": "MyPassword123"
}
```

### 3. Войти с новым паролем
```
POST {{base_url}}/api/auth/login
Body (JSON):
{
  "telephone": "+998901234567",
  "password": "MyPassword123"
}
```

---

## Рекомендации по дальнейшему развитию

1. **Добавить rate limiting** - ограничить количество попыток установки пароля
   ```python
   # Не более 3 попыток в час для одного номера телефона
   ```

2. **SMS уведомления** при установке/смене пароля
   ```python
   # "Ваш пароль был изменён. Если это не вы, свяжитесь с поддержкой"
   ```

3. **Добавить дополнительную проверку** (опционально):
   - Имя пользователя + номер телефона
   - Последние 4 цифры последнего заказа
   - Контрольный вопрос

4. **Логирование всех изменений паролей** для безопасности
   ```python
   # Сохранять: timestamp, IP, user_id, success/failure
   ```

5. **Временное блокирование** после нескольких неудачных попыток
   ```python
   # Блокировка на 1 час после 5 неудачных попыток
   ```

---

## Заключение

Новый эндпоинт `/api/auth/set-password` решает проблему гостевых пользователей максимально простым способом - **без токена и без OTP**. Пользователю нужен только его номер телефона.

**Ключевые преимущества:**
- ✅ Максимальная простота использования
- ✅ Не требует токена
- ✅ Не требует старого пароля
- ✅ Не требует OTP/SMS
- ✅ Работает сразу после создания заказа

**⚠️ Важно для безопасности:**
- Добавьте rate limiting
- Отправляйте SMS уведомления
- Логируйте все изменения паролей
- Рассмотрите дополнительную проверку личности

**Простой flow для пользователя:**
1. Создаёт заказ без регистрации → автоматически создаётся аккаунт
2. Устанавливает пароль через номер телефона → получает доступ к аккаунту
3. Входит в систему → просматривает историю заказов
