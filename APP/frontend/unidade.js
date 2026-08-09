const selectUnidade = document.getElementById("select-unidade");
const btnContinuar = document.getElementById("btn-continuar");
const erroMsg = document.getElementById("erro-msg");

async function carregarUnidades() {
  try {
    const resp = await fetch(`${API_URL}/api/unidades`);
    const data = await resp.json();
    const unidades = (data.unidades || []).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

    selectUnidade.innerHTML = '<option value="">Selecione uma unidade...</option>';
    unidades.forEach((u) => {
      const opt = document.createElement("option");
      opt.value = u.id;
      opt.dataset.nome = u.nome;
      opt.textContent = u.nome;
      selectUnidade.appendChild(opt);
    });
  } catch (err) {
    erroMsg.textContent = "Não foi possível carregar as unidades.";
  }
}

btnContinuar.addEventListener("click", () => {
  const opt = selectUnidade.options[selectUnidade.selectedIndex];
  if (!selectUnidade.value) {
    erroMsg.textContent = "Selecione uma unidade para continuar.";
    return;
  }
  sessionStorage.setItem("unidade_id", selectUnidade.value);
  sessionStorage.setItem("unidade_nome", opt.dataset.nome);

  if (opt.dataset.nome === "ADMIN") {
    window.location.href = "login-admin.html";
  } else {
    window.location.href = "login-aluno.html";
  }
});

carregarUnidades();
