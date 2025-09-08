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
 * @param {boolean} finalize
 */
async function postAnswers(finalize = false) {
  const answersData = collectPayload();
  
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
      const errorData = await res.json().catch(() => ({ detail: 'Ошибка сохранения' }));
      console.error('Save error:', errorData);
      alert(errorData.detail || 'Ошибка сохранения');
    } else if (finalize) {
      showThanksModal();
    }
  } catch (error) {
    console.error('Network error:', error);
    alert('Сетевая ошибка. Проверьте подключение к интернету.');
  }
}

saveBtn?.addEventListener('click', (e) => { 
  e.preventDefault(); 
  postAnswers(false); 
  const originalText = e.target.textContent;
  e.target.textContent = 'Сохранено!';
  setTimeout(() => { e.target.textContent = originalText; }, 1500);
});

submitBtn?.addEventListener('click', (e) => { 
  e.preventDefault(); 
  if (form.checkValidity()) {
    postAnswers(true);
  } else {
    form.reportValidity();
    alert('Пожалуйста, заполните все обязательные поля (*)');
  }
});

let autoSaveTimeout;
form.addEventListener('input', () => {
  clearTimeout(autoSaveTimeout);
  autoSaveTimeout = setTimeout(() => postAnswers(false), 600);
});

document.querySelectorAll('input[type=range]').forEach(r => {
  const out = r.parentElement.querySelector('.scale-value');
  const set = () => out && (out.textContent = r.value);
  r.addEventListener('input', set);
  set();
});

function showThanksModal() {
  let modal = document.getElementById('thanks-modal');
  if (!modal) {
    const div = document.createElement('div');
    div.id = 'thanks-modal';
    div.style.position = 'fixed';
    div.style.inset = '0';
    div.style.background = 'rgba(0,0,0,0.5)';
    div.style.display = 'flex';
    div.style.alignItems = 'center';
    div.style.justifyContent = 'center';
    div.style.zIndex = '1050';
    div.innerHTML = `
      <div style="padding:24px;border-radius:8px;max-width:480px;width:90%;text-align:center">
        <h3 class="mono mb-2">Спасибо!</h3>
        <p>Ваши ответы записаны.</p>
        <div class="mt-3 d-flex gap-2 justify-content-center">
          <button id="thanks-close" class="btn btn-brutal">Чики-бамбони</button>
        </div>
      </div>`;
    document.body.appendChild(div);
    div.addEventListener('click', (e) => { if (e.target === div) div.remove(); });
    div.querySelector('#thanks-close').addEventListener('click', () => div.remove());
    modal = div;
  }
  modal.style.display = 'flex';
}