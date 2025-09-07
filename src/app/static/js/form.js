// app/static/js/form.js
const form = document.querySelector('#survey-form');
const saveBtn = document.querySelector('#btn-save');
const submitBtn = document.querySelector('#btn-submit');

/**
 * Собирает данные из формы в формате, который ожидает новый API.
 * @returns {Array<Object>} Массив объектов-ответов.
 * Пример: [{ question_id: '...', response_text: '...', selected_option_ids: [] }]
 */
function collectPayload() {
  const answers = []; // ИЗМЕНЕНИЕ: Раньше был объект `data = {}`, теперь массив `answers = []`
  
  document.querySelectorAll('.q-block').forEach(bl => {
    const qid = bl.dataset.qid;
    if (!qid) return;

    // Создаем шаблон объекта ответа для этого вопроса
    const answer = {
      question_id: qid,
      response_text: null,
      selected_option_ids: [],
    };

    // 1. Ищем текстовые ответы (text, textarea, range)
    const textInput = bl.querySelector('input[type="text"], input[type="range"], textarea');
    if (textInput) {
      answer.response_text = textInput.value;
    }

    // 2. Ищем ответ для radio button
    const radioInput = bl.querySelector('input[type="radio"]:checked');
    if (radioInput) {
      // API ожидает массив ID, даже для radio
      answer.selected_option_ids.push(radioInput.value);
    }

    // 3. Ищем ответы для checkbox'ов
    const checkboxInputs = bl.querySelectorAll('input[type="checkbox"]:checked');
    if (checkboxInputs.length > 0) {
      checkboxInputs.forEach(cb => answer.selected_option_ids.push(cb.value));
    }
    
    // Добавляем собранный объект ответа в общий массив
    answers.push(answer);
  });
  
  return answers;
}

/**
 * Отправляет ответы на сервер. Логика почти не изменилась.
 * @param {boolean} finalize - Если true, отправляет как финальный ответ.
 */
async function postAnswers(finalize = false) {
  // Вызываем обновленную функцию collectPayload
  const answersData = collectPayload();
  
  // Собираем финальный payload для API
  const payload = { 
    answers: answersData, 
    csrf_token: decodeURIComponent(window.__CSRF__ || '') 
  };
  
  const url = `${form.dataset.api}${finalize ? '&final=true' : ''}`;
  try {
    const res = await fetch(url, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify(payload) 
    });

    if (!res.ok) {
      // Попробуем получить текст ошибки с сервера
      const errorData = await res.json().catch(() => ({ detail: 'Ошибка сохранения' }));
      console.error('Save error:', errorData);
      alert(errorData.detail || 'Ошибка сохранения');
    } else if (finalize) {
      window.location.href = form.dataset.done;
    }
  } catch (error) {
    console.error('Network error:', error);
    alert('Сетевая ошибка. Проверьте подключение к интернету.');
  }
}

// --- Обработчики событий остались без изменений ---

saveBtn?.addEventListener('click', (e) => { 
  e.preventDefault(); 
  postAnswers(false); 
  // Можно добавить визуальный фидбек для пользователя
  const originalText = e.target.textContent;
  e.target.textContent = 'Сохранено!';
  setTimeout(() => { e.target.textContent = originalText; }, 1500);
});

submitBtn?.addEventListener('click', (e) => { 
  e.preventDefault(); 
  // Простая проверка на заполнение обязательных полей перед отправкой
  if (form.checkValidity()) {
    postAnswers(true);
  } else {
    form.reportValidity();
    alert('Пожалуйста, заполните все обязательные поля (*)');
  }
});

// Логика автосохранения
let autoSaveTimeout;
form.addEventListener('input', () => {
  clearTimeout(autoSaveTimeout);
  autoSaveTimeout = setTimeout(() => postAnswers(false), 1200); // Немного увеличил задержку
});

// UI для range-слайдера (без изменений)
document.querySelectorAll('input[type=range]').forEach(r => {
  const out = r.parentElement.querySelector('.scale-value');
  const set = () => out && (out.textContent = r.value);
  r.addEventListener('input', set);
  set();
});