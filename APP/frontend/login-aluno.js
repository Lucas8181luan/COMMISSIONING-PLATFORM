const unidadeId = sessionStorage.getItem("unidade_id");
const unidadeNome = sessionStorage.getItem("unidade_nome");

if (!unidadeId) {
  window.location.href = "unidade.html";
}

document.getElementById("unidade-atual").textContent = `Unidade: ${unidadeNome || "—"}`;

const tabLogin = document.getElementById("tab-login");
const tabCadastro = document.getElementById("tab-cadastro");
const formLogin = document.getElementById("form-login");
const formCadastro = document.getElementById("form-cadastro");
const erroMsg = document.getElementById("erro-msg");

tabLogin.addEventListener("click", () => {
  tabLogin.classList.add("ativo");
  tabCadastro.classList.remove("ativo");
  formLogin.style.display = "block";
  formCadastro.style.display = "none";
  erroMsg.textContent = "";
});

tabCadastro.addEventListener("click", () => {
  tabCadastro.classList.add("ativo");
  tabLogin.classList.remove("ativo");
  formCadastro.style.display = "block";
  formLogin.style.display = "none";
  erroMsg.textContent = "";
});

formLogin.addEventListener("submit", async (e) => {
  e.preventDefault();
  erroMsg.textContent = "";
  const cpf = document.getElementById("login-cpf").value.trim();
  const senha = document.getElementById("login-senha").value;

  try {
    const resp = await fetch(`${API_URL}/api/aluno/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cpf, senha, unidade_id: unidadeId }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      erroMsg.textContent = data.erro || "Erro ao entrar.";
      return;
    }
    window.location.href = "aluno-dashboard.html";
  } catch (err) {
    erroMsg.textContent = "Não foi possível conectar ao servidor.";
  }
});

formCadastro.addEventListener("submit", async (e) => {
  e.preventDefault();
  erroMsg.textContent = "";
  const nome = document.getElementById("cad-nome").value.trim();
  const cpf = document.getElementById("cad-cpf").value.trim();
  const email = document.getElementById("cad-email").value.trim();
  const senha = document.getElementById("cad-senha").value;

  try {
    const resp = await fetch(`${API_URL}/api/aluno/cadastro`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, cpf, email, senha, unidade_id: unidadeId }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      erroMsg.textContent = data.erro || "Erro ao cadastrar.";
      return;
    }
    window.location.href = "aluno-dashboard.html";
  } catch (err) {
    erroMsg.textContent = "Não foi possível conectar ao servidor.";
  }
});
