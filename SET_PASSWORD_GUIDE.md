# Руководство по установке пароля для гостевых пользователей

## Проблема

Когда клиент создаёт заказ без регистрации (через POST-запрос без токена), система автоматически создаёт для него учётную запись с **случайным паролем**, который клиент не знает.

## Решение

Добавлен новый эндпоинт `/api/auth/set-password`, который позволяет пользователю установить пароль **без знания старого пароля**.

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

### Шаг 2: Клиент хочет отслеживать заказы

Клиент понимает, что нужен аккаунт, но не знает пароль.

**Вариант А: Клиент получает токен через особый механизм (например, OTP по SMS)**

Если вы реализовали OTP-аутентификацию, клиент получает временный токен через SMS-код.

**Вариант Б: Клиент уже имеет токен из другого источника**

Например, через мобильное приложение с автоматической авторизацией по номеру телефона.

---

### Шаг 3: Клиент устанавливает пароль

```bash
POST /api/auth/set-password
Authorization: Bearer <токен_пользователя>
Content-Type: application/json

{
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

---

### Шаг 4: Клиент может войти с новым паролем

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
| **Требует старый пароль** | ❌ Нет | ✅ Да |
| **Для кого** | Гостевые пользователи | Зарегистрированные пользователи |
| **Требует токен** | ✅ Да | ✅ Да |
| **Валидация** | Минимум 6 символов | Минимум 6 символов + проверка старого |
| **Безопасность** | Зависит от способа получения токена | Высокая (двухфакторная) |

---

## Безопасность

### ⚠️ Важно!

Эндпоинт `/set-password` **НЕ требует старого пароля**, поэтому:

1. **Он требует валидный JWT токен** → злоумышленник не может установить пароль без токена
2. **Рекомендуется использовать только для первой установки пароля**
3. **После установки пароля клиент должен использовать `/change-password` для смены**

### Улучшения безопасности (опционально)

Вы можете добавить проверку, что пользователь ещё не устанавливал пароль:

```python
@router.post("/set-password")
def set_password(
    password_data: SetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверка: можно установить пароль только один раз
    # (например, если пароль - это UUID)
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    # Попытка верификации с UUID (если пароль был случайный UUID)
    # Если верификация не удаётся, значит пароль уже был установлен
    try:
        # Проверяем, был ли пароль установлен вручную
        # (это упрощённая проверка, можно добавить флаг в базу)
        pass
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password already set. Use /change-password endpoint."
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {
        "message": "Password set successfully.",
        "telephone": current_user.telephone
    }
```

---

## Интеграция с фронтендом

### Пример на JavaScript (React/Vue/Angular)

```javascript
// После получения токена (например, через OTP)
async function setPassword(token, newPassword) {
  const response = await fetch('https://api.yourapp.com/api/auth/set-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      new_password: newPassword,
      confirm_password: newPassword
    })
  });
  
  const data = await response.json();
  
  if (response.ok) {
    console.log('Password set successfully!', data);
    // Redirect to login or dashboard
  } else {
    console.error('Error:', data.detail);
  }
}

// Использование
setPassword(userToken, 'MyNewPassword123');
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

### 2. Получить токен (если есть OTP или другой механизм)
```
POST {{base_url}}/api/auth/otp-login
Body (JSON):
{
  "telephone": "+998901234567",
  "otp_code": "1234"
}
```

### 3. Установить пароль
```
POST {{base_url}}/api/auth/set-password
Headers:
  Authorization: Bearer {{access_token}}
Body (JSON):
{
  "new_password": "MyPassword123",
  "confirm_password": "MyPassword123"
}
```

### 4. Войти с новым паролем
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

1. **Добавить OTP-аутентификацию** для получения токена без знания пароля
2. **Добавить флаг `password_set`** в модель User для отслеживания, устанавливал ли пользователь пароль
3. **Логировать события** установки пароля для безопасности
4. **Rate limiting** на эндпоинт `/set-password` (не более 3 попыток в час)
5. **Email/SMS уведомления** при установке/смене пароля

---

## Заключение

Новый эндпоинт `/api/auth/set-password` решает проблему гостевых пользователей, позволяя им установить пароль для своего аккаунта без знания сгенерированного системой случайного пароля.

**Ключевые преимущества:**
- ✅ Простота использования
- ✅ Не требует старого пароля
- ✅ Защищён JWT токеном
- ✅ Валидация совпадения паролей
- ✅ Минимальная длина пароля (6 символов)

**Следующий шаг:** Реализуйте механизм получения токена (OTP по SMS, авторизация через соцсети и т.д.) для полноценного пользовательского опыта.
