"""
Конфигурация приложения "Тайный Санта OVERSUN"
"""

# Код администратора (измените на свой)
# Для продакшена рекомендуется использовать переменную окружения
import os
ADMIN_CODE = os.environ.get('ADMIN_CODE', 'oversun2025')

# Настройки базы данных
DATABASE = "secret_santa.db"

# Настройки Flask
# Для продакшена рекомендуется использовать переменную окружения
SECRET_KEY = os.environ.get('SECRET_KEY', 'oversun-secret-santa-2025-secret-key-change-in-production')

# Настройки игры
COMPANY_NAME = "OVERSUN"
GAME_NAME = "Тайный Санта"

# Статусы игры
STATUS_REGISTRATION = "registration"
STATUS_COMPLETED = "completed"
STATUS_RESET = "reset"

