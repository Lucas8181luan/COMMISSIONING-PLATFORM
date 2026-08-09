const params = new URLSearchParams(window.location.search);
const codigoRef = params.get("ref");

const form = document.getElementById("form-matricula");
const btnEnviar = document.getElementById("btn-enviar");
const msg = document.getElementById("msg");

if (!codigoRef) {
  msg.textContent = "Link de indicação inválido ou incompleto.";
  form.querySelectorAll("input, button").forEach((el) => (el.disabled = true));
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  msg.textContent = "";
  btnEnviar.disabled = true;
  btnEnviar.textContent = "Enviando...";

  const nome = document.getElementById("nome").value.trim();
  const cpf = document.getElementById("cpf").value.trim();

  try {
    const resp = await fetch(`${API_URL}/api/indicacao/publica`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codigo_afiliado: codigoRef, nome_indicado: nome, cpf_indicado: cpf }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      msg.textContent = data.erro || "Erro ao enviar.";
      btnEnviar.disabled = false;
      btnEnviar.textContent = "Enviar interesse";
      return;
    }
    msg.className = "erro-msg sucesso";
    msg.textContent = "Interesse registrado! A equipe IFP entrará em contato para concluir sua matrícula.";
    form.querySelectorAll("input, button").forEach((el) => (el.disabled = true));
  } catch (err) {
    msg.textContent = "Não foi possível conectar ao servidor.";
    btnEnviar.disabled = false;
    btnEnviar.textContent = "Enviar interesse";
  }
});
