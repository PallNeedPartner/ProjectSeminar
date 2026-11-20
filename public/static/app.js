document.addEventListener('DOMContentLoaded', () => {
  const globalSearch = document.getElementById('globalSearch');
  if (globalSearch) {
    globalSearch.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      const query = globalSearch.value.trim().toLowerCase();
      if (!query) return;
      const link = [...document.querySelectorAll('.main-nav a')].find(a => a.textContent.toLowerCase().includes(query));
      if (link) window.location.href = link.href;
      else alert('Menu yang dicari tidak ditemukan. Coba kata kunci lain.');
    });
  }

  const filterTable = (inputId, tableId) => {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    input.addEventListener('input', () => {
      const query = input.value.toLowerCase();
      table.querySelectorAll('tbody tr').forEach(row => {
        row.hidden = !row.textContent.toLowerCase().includes(query);
      });
    });
  };
  filterTable('patient-search', 'patient-table');
  filterTable('user-search', 'user-table');

  const vaccineSearch = document.getElementById('vaccine-search');
  const vaccineGrid = document.getElementById('vaccine-grid');
  if (vaccineSearch && vaccineGrid) {
    vaccineSearch.addEventListener('input', () => {
      const query = vaccineSearch.value.toLowerCase();
      vaccineGrid.querySelectorAll('.vaccine-card').forEach(card => {
        card.hidden = !card.textContent.toLowerCase().includes(query);
      });
    });
  }

  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', (event) => {
      event.preventDefault();
      sendQuestion();
    });
  }
});

function askExample(question) {
  const input = document.getElementById('question');
  if (!input) return;
  input.value = question;
  input.focus();
}
function sendQuestion() {
  const input = document.getElementById('question');
  const box = document.getElementById('chat-box');
  if (!input || !box || !input.value.trim()) return;
  const question = input.value.trim();
  const user = document.createElement('div');
  user.className = 'chat-message user';
  user.textContent = question;
  box.appendChild(user);
  const reply = document.createElement('div');
  reply.className = 'chat-message bot';
  reply.textContent = 'Terima kasih atas pertanyaannya. Fitur integrasi AI belum dihubungkan ke backend. Untuk informasi yang sesuai kondisi Anda, silakan konsultasikan dengan tenaga kesehatan Puskesmas.';
  box.appendChild(reply);
  input.value = '';
  box.scrollTop = box.scrollHeight;
}
