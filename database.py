"""
Модели и работа с базой данных
"""

import sqlite3
from datetime import datetime
from config import DATABASE, STATUS_REGISTRATION, STATUS_COMPLETED, STATUS_RESET


def get_db():
    """Получить соединение с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация базы данных"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица участников
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            wishlist TEXT,
            recipient_id INTEGER,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recipient_id) REFERENCES participants(id)
        )
    ''')
    
    # Таблица состояния игры
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            drawn_at TIMESTAMP,
            price_limit REAL
        )
    ''')
    
    # Добавляем колонку price_limit, если её нет (для существующих БД)
    try:
        cursor.execute('ALTER TABLE game_state ADD COLUMN price_limit REAL')
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
    # Проверка наличия записи о состоянии игры
    cursor.execute('SELECT COUNT(*) FROM game_state')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO game_state (status) VALUES (?)
        ''', (STATUS_REGISTRATION,))
    
    conn.commit()
    conn.close()


def add_participant(name, email, wishlist=None):
    """Добавить участника"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO participants (name, email, wishlist)
            VALUES (?, ?, ?)
        ''', (name, email, wishlist))
        conn.commit()
        return True, "Участник успешно зарегистрирован"
    except sqlite3.IntegrityError:
        return False, "Участник с таким email уже зарегистрирован"
    finally:
        conn.close()


def get_participant_by_email(email):
    """Получить участника по email"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM participants WHERE email = ?', (email,))
    participant = cursor.fetchone()
    conn.close()
    return dict(participant) if participant else None


def get_all_participants():
    """Получить всех участников"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM participants ORDER BY registered_at')
    participants = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return participants


def get_game_state():
    """Получить состояние игры"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM game_state ORDER BY id DESC LIMIT 1')
    state = cursor.fetchone()
    conn.close()
    return dict(state) if state else None


def update_game_status(status):
    """Обновить статус игры"""
    conn = get_db()
    cursor = conn.cursor()
    
    if status == STATUS_COMPLETED:
        cursor.execute('''
            UPDATE game_state 
            SET status = ?, drawn_at = ?
            WHERE id = (SELECT id FROM game_state ORDER BY id DESC LIMIT 1)
        ''', (status, datetime.now()))
    else:
        cursor.execute('''
            UPDATE game_state 
            SET status = ?, drawn_at = NULL
            WHERE id = (SELECT id FROM game_state ORDER BY id DESC LIMIT 1)
        ''', (status,))
    
    conn.commit()
    conn.close()


def update_price_limit(price_limit):
    """Обновить лимит цены подарка"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE game_state 
        SET price_limit = ?
        WHERE id = (SELECT id FROM game_state ORDER BY id DESC LIMIT 1)
    ''', (price_limit,))
    
    conn.commit()
    conn.close()


def get_participant_by_id(participant_id):
    """Получить участника по ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM participants WHERE id = ?', (participant_id,))
    participant = cursor.fetchone()
    conn.close()
    return dict(participant) if participant else None


def update_participant(participant_id, name, email, wishlist):
    """Обновить данные участника"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Проверяем, не занят ли email другим участником
        cursor.execute('SELECT id FROM participants WHERE email = ? AND id != ?', (email, participant_id))
        if cursor.fetchone():
            return False, "Email уже используется другим участником"
        
        cursor.execute('''
            UPDATE participants 
            SET name = ?, email = ?, wishlist = ?
            WHERE id = ?
        ''', (name, email, wishlist if wishlist else None, participant_id))
        
        conn.commit()
        return True, "Данные участника успешно обновлены"
    except sqlite3.IntegrityError:
        return False, "Ошибка при обновлении данных"
    finally:
        conn.close()


def assign_recipients(assignments):
    """
    Назначить получателей подарков
    assignments: список кортежей (participant_id, recipient_id)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    for participant_id, recipient_id in assignments:
        cursor.execute('''
            UPDATE participants 
            SET recipient_id = ? 
            WHERE id = ?
        ''', (recipient_id, participant_id))
    
    conn.commit()
    conn.close()


def get_recipient_info(participant_id):
    """Получить информацию о получателе подарка"""
    conn = get_db()
    cursor = conn.cursor()
    # Сначала получаем participant с его recipient_id
    cursor.execute('SELECT * FROM participants WHERE id = ?', (participant_id,))
    participant = cursor.fetchone()
    
    if not participant or not participant['recipient_id']:
        conn.close()
        return None
    
    # Затем получаем информацию о получателе
    cursor.execute('SELECT * FROM participants WHERE id = ?', (participant['recipient_id'],))
    recipient = cursor.fetchone()
    conn.close()
    
    if recipient:
        return {
            'recipient_name': recipient['name'],
            'recipient_email': recipient['email'],
            'recipient_wishlist': recipient['wishlist']
        }
    return None


def reset_game():
    """Сбросить игру - очистить все данные"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Удалить все назначения
    cursor.execute('UPDATE participants SET recipient_id = NULL')
    
    # Удалить всех участников
    cursor.execute('DELETE FROM participants')
    
    # Сбросить статус игры
    cursor.execute('''
        UPDATE game_state 
        SET status = ?, drawn_at = NULL
        WHERE id = (SELECT id FROM game_state ORDER BY id DESC LIMIT 1)
    ''', (STATUS_RESET,))
    
    conn.commit()
    conn.close()

