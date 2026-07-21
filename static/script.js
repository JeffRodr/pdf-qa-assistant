const chatEl = document.getElementById("chat");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("question-input");
const badgeEl = document.getElementById("status-badge");

function addMessage(text, role, sources) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;

  if (sources && sources.length) {
    const src = document.createElement("div");
    src.className = "sources";
    src.textContent = "Fuentes: " + sources
      .map((s) => `${s.source} (pág. ${s.page})`)
      .join(", ");
    div.appendChild(src);
  }

  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.ready) {
      badgeEl.textContent = `${data.documents} PDF · ${data.chunks} fragmentos`;
      badgeEl.className = "badge ready";
    } else {
      badgeEl.textContent = "sin documentos indexados";
      badgeEl.className = "badge error";
    }
  } catch {
    badgeEl.textContent = "sin conexión";
    badgeEl.className = "badge error";
  }
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = inputEl.value.trim();
  if (!question) return;

  addMessage(question, "user");
  inputEl.value = "";
  inputEl.disabled = true;
  formEl.querySelector("button").disabled = true;

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    if (!res.ok) {
      addMessage(data.error || "Ocurrió un error.", "error");
    } else {
      addMessage(data.answer, "bot", data.sources);
    }
  } catch {
    addMessage("No se pudo contactar al servidor.", "error");
  } finally {
    inputEl.disabled = false;
    formEl.querySelector("button").disabled = false;
    inputEl.focus();
  }
});

refreshStatus();
