// app/static/js/form.js
const form = document.querySelector('#survey-form');
const saveBtn = document.querySelector('#btn-save');
const submitBtn = document.querySelector('#btn-submit');

function collectPayload() {
  const data = {};
  document.querySelectorAll('.q-block').forEach(bl => {
    const qid = bl.dataset.qid;
    const inputs = bl.querySelectorAll('[name="'+qid+'"], [name="'+qid+'[]"]');
    if (!inputs.length) return;
    const el = inputs[0];
    if (el.type === 'radio') {
      const chosen = bl.querySelector('input[type=radio]:checked');
      data[qid] = chosen ? chosen.value : null;
    } else if (el.type === 'checkbox') {
      data[qid] = Array.from(bl.querySelectorAll('input[type=checkbox]:checked')).map(i => i.value);
    } else if (el.type === 'range' || el.type === 'text' || el.tagName === 'TEXTAREA') {
      data[qid] = el.value;
    }
  });
  return data;
}

async function postAnswers(finalize=false) {
  const payload = { answers: collectPayload(), csrf_token: decodeURIComponent(window.__CSRF__ || '') };
  const url = `${form.dataset.api}${finalize ? '&final=1' : '&draft=1'}`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) {
    alert('Ошибка сохранения');
  } else if (finalize) {
    window.location.href = form.dataset.done;
  }
}

saveBtn?.addEventListener('click', (e) => { e.preventDefault(); postAnswers(false); });
submitBtn?.addEventListener('click', (e) => { e.preventDefault(); postAnswers(true); });

let t;
form.addEventListener('input', () => {
  clearTimeout(t);
  t = setTimeout(() => postAnswers(false), 800);
});

// show live value for range
document.querySelectorAll('input[type=range]').forEach(r => {
  const out = r.parentElement.querySelector('.scale-value');
  const set = () => out && (out.textContent = r.value);
  r.addEventListener('input', set);
  set();
});