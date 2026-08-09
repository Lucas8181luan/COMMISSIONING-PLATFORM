const form = document.getElementById("form-login");
const btnEntrar = document.getElementById("btn-entrar");
const erroMsg = document.getElementById("erro-msg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  erroMsg.textContent = "";
  btnEntrar.disabled = true;
  btnEntrar.textContent = "Entrando...";

  const usuario = document.getElementById("usuario").value.trim();
  const senha = document.getElementById("senha").value;

  try {
    const resp = await fetch(`${API_URL}/api/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, senha }),
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      erroMsg.textContent = data.erro || "Usuário ou senha inválidos.";
      btnEntrar.disabled = false;
      btnEntrar.textContent = "Entrar";
      return;
    }

    window.location.href = "dashboard.html";
  } catch (err) {
    erroMsg.textContent = "Não foi possível conectar ao servidor.";
    btnEntrar.disabled = false;
    btnEntrar.textContent = "Entrar";
  }
});
