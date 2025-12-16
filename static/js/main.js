/**
 * Основной JavaScript для приложения "Тайный Санта OVERSUN"
 */

// Проверка регистрации по email на главной странице
document.addEventListener('DOMContentLoaded', function() {
    const checkForm = document.getElementById('checkForm');
    const checkResult = document.getElementById('checkResult');
    
    if (checkForm) {
        checkForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('checkEmail').value.trim();
            
            if (!email) {
                checkResult.innerHTML = '<p class="error">Пожалуйста, введите email</p>';
                return;
            }
            
            checkResult.innerHTML = '<p>Проверка...</p>';
            
            try {
                const response = await fetch('/participant/check', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email: email })
                });
                
                const data = await response.json();
                
                if (data.exists) {
                    checkResult.innerHTML = `
                        <p class="success">Участник найден!</p>
                        <a href="${data.url}" class="btn btn-primary" style="margin-top: 10px; display: inline-block;">
                            Перейти в личный кабинет
                        </a>
                    `;
                } else {
                    checkResult.innerHTML = '<p class="error">Участник с таким email не найден. Зарегистрируйтесь, пожалуйста.</p>';
                }
            } catch (error) {
                checkResult.innerHTML = '<p class="error">Ошибка при проверке. Попробуйте позже.</p>';
            }
        });
    }
    
    // Плавная прокрутка для якорей
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Автоматическое скрытие алертов через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });
});

// Валидация форм
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Добавление визуальной обратной связи для форм
document.querySelectorAll('input, textarea').forEach(input => {
    input.addEventListener('blur', function() {
        if (this.hasAttribute('required') && !this.value.trim()) {
            this.style.borderColor = '#dc3545';
        } else {
            this.style.borderColor = '';
        }
    });
    
    input.addEventListener('input', function() {
        if (this.style.borderColor === 'rgb(220, 53, 69)') {
            this.style.borderColor = '';
        }
    });
});

