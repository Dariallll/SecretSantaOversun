"""
Главный файл Flask приложения "Тайный Санта OVERSUN"
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import random
from database import (
    init_db, add_participant, get_participant_by_email, get_all_participants,
    get_game_state, update_game_status, assign_recipients, get_recipient_info, reset_game,
    update_price_limit, get_participant_by_id, update_participant
)
from config import ADMIN_CODE, STATUS_REGISTRATION, STATUS_COMPLETED, STATUS_RESET, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Инициализация базы данных при запуске
init_db()


def is_admin():
    """Проверка, является ли пользователь администратором"""
    return session.get('is_admin', False)


def perform_draw():
    """
    Выполнить жеребьёвку - распределить участников
    Алгоритм: циклическая перестановка с проверкой самоназначения
    """
    participants = get_all_participants()
    
    if len(participants) < 2:
        return False, "Недостаточно участников для жеребьёвки (минимум 2)"
    
    # Получаем список ID участников
    participant_ids = [p['id'] for p in participants]
    
    # Создаем перестановку (shuffle)
    recipient_ids = participant_ids.copy()
    random.shuffle(recipient_ids)
    
    # Проверяем и исправляем самоназначения
    max_attempts = 100
    attempts = 0
    
    while attempts < max_attempts:
        # Проверяем наличие самоназначений
        has_self_assignment = any(
            participant_ids[i] == recipient_ids[i] 
            for i in range(len(participant_ids))
        )
        
        if not has_self_assignment:
            break
        
        # Если есть самоназначение, перемешиваем снова
        random.shuffle(recipient_ids)
        attempts += 1
    
    # Если после всех попыток есть самоназначение, используем циклический сдвиг
    if any(participant_ids[i] == recipient_ids[i] for i in range(len(participant_ids))):
        # Циклический сдвиг на 1 позицию
        recipient_ids = participant_ids[1:] + [participant_ids[0]]
    
    # Формируем пары (участник -> получатель)
    assignments = list(zip(participant_ids, recipient_ids))
    
    # Сохраняем в БД
    assign_recipients(assignments)
    
    # Обновляем статус игры
    update_game_status(STATUS_COMPLETED)
    
    return True, "Жеребьёвка успешно выполнена"


# ==================== ПУБЛИЧНЫЕ СТРАНИЦЫ ====================

@app.route('/')
def index():
    """Главная страница"""
    game_state = get_game_state()
    return render_template('index.html', game_state=game_state)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация участника"""
    game_state = get_game_state()
    
    # Проверка, можно ли регистрироваться
    if game_state and game_state['status'] == STATUS_COMPLETED:
        return render_template('error.html', 
                             message="Регистрация закрыта. Жеребьёвка уже проведена.")
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        wishlist = request.form.get('wishlist', '').strip()
        
        # Валидация
        if not name or not email:
            return render_template('register.html', 
                                 error="Пожалуйста, заполните все обязательные поля",
                                 game_state=game_state)
        
        # Добавление участника
        success, message = add_participant(name, email, wishlist if wishlist else None)
        
        if success:
            return redirect(url_for('participant', email=email))
        else:
            return render_template('register.html', 
                                 error=message,
                                 game_state=game_state)
    
    return render_template('register.html', game_state=game_state)


@app.route('/participant/<email>')
def participant(email):
    """Личный кабинет участника"""
    participant_data = get_participant_by_email(email)
    
    if not participant_data:
        return render_template('error.html', 
                             message="Участник не найден")
    
    game_state = get_game_state()
    
    # Если жеребьёвка проведена, показываем информацию о получателе
    recipient_info = None
    if game_state and game_state['status'] == STATUS_COMPLETED:
        recipient_info = get_recipient_info(participant_data['id'])
    
    return render_template('participant.html', 
                         participant=participant_data,
                         recipient_info=recipient_info,
                         game_state=game_state)


@app.route('/participant/check', methods=['POST'])
def check_participant():
    """Проверка регистрации по email (AJAX)"""
    email = request.json.get('email', '').strip()
    participant_data = get_participant_by_email(email)
    
    if participant_data:
        return jsonify({'exists': True, 'url': url_for('participant', email=email)})
    else:
        return jsonify({'exists': False})


# ==================== АДМИНИСТРАТИВНЫЕ СТРАНИЦЫ ====================

@app.route('/admin')
def admin_login():
    """Страница входа администратора"""
    return render_template('admin.html', login_page=True)


@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    """Обработка входа администратора"""
    code = request.form.get('code', '').strip()
    
    if code == ADMIN_CODE:
        session['is_admin'] = True
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template('admin.html', 
                             login_page=True,
                             error="Неверный код администратора")


@app.route('/admin/dashboard')
def admin_dashboard():
    """Административная панель"""
    if not is_admin():
        return render_template('error.html', 
                             message="Доступ запрещен. Требуется авторизация администратора.")
    
    participants = get_all_participants()
    game_state = get_game_state()
    
    # Получаем информацию о парах, если жеребьёвка проведена
    pairs = []
    if game_state and game_state['status'] == STATUS_COMPLETED:
        for p in participants:
            recipient_info = get_recipient_info(p['id'])
            if recipient_info and recipient_info.get('recipient_name'):
                pairs.append({
                    'giver': p,
                    'recipient': {
                        'name': recipient_info['recipient_name'],
                        'email': recipient_info['recipient_email'],
                        'wishlist': recipient_info['recipient_wishlist']
                    }
                })
    
    return render_template('admin.html', 
                         login_page=False,
                         participants=participants,
                         pairs=pairs,
                         game_state=game_state)


@app.route('/api/admin/participants')
def api_participants():
    """API: Список всех участников"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    participants = get_all_participants()
    return jsonify({'participants': participants})


@app.route('/api/admin/game-state')
def api_game_state():
    """API: Статус игры"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    game_state = get_game_state()
    return jsonify({'game_state': game_state})


@app.route('/api/admin/draw', methods=['POST'])
def api_draw():
    """API: Запуск жеребьёвки"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    game_state = get_game_state()
    
    # Проверка, не проведена ли уже жеребьёвка
    if game_state and game_state['status'] == STATUS_COMPLETED:
        return jsonify({'success': False, 
                       'message': 'Жеребьёвка уже проведена'}), 400
    
    success, message = perform_draw()
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400


@app.route('/api/admin/reset', methods=['POST'])
def api_reset():
    """API: Сброс игры"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    reset_game()
    update_game_status(STATUS_REGISTRATION)
    
    return jsonify({'success': True, 'message': 'Игра успешно сброшена'})


@app.route('/api/admin/price-limit', methods=['POST'])
def api_set_price_limit():
    """API: Установка лимита цены"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    price_limit = data.get('price_limit')
    
    if price_limit is None:
        return jsonify({'success': False, 'message': 'Лимит цены не указан'}), 400
    
    try:
        price_limit = float(price_limit)
        if price_limit < 0:
            return jsonify({'success': False, 'message': 'Лимит цены не может быть отрицательным'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Неверный формат лимита цены'}), 400
    
    update_price_limit(price_limit)
    return jsonify({'success': True, 'message': f'Лимит цены установлен: {price_limit} руб.'})


@app.route('/api/admin/participant/<int:participant_id>', methods=['GET'])
def api_get_participant(participant_id):
    """API: Получить участника для редактирования"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    participant = get_participant_by_id(participant_id)
    if not participant:
        return jsonify({'error': 'Participant not found'}), 404
    
    return jsonify({'participant': participant})


@app.route('/api/admin/participant/<int:participant_id>', methods=['PUT'])
def api_update_participant(participant_id):
    """API: Обновить данные участника"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    wishlist = data.get('wishlist', '').strip()
    
    if not name or not email:
        return jsonify({'success': False, 'message': 'Имя и email обязательны'}), 400
    
    success, message = update_participant(participant_id, name, email, wishlist)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400


@app.route('/admin/logout')
def admin_logout():
    """Выход администратора"""
    session.pop('is_admin', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Для локальной разработки
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)

