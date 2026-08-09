const btnSair = document.getElementById("btn-sair");
const filtroUnidade = document.getElementById("filtro-unidade");

function formatarMoeda(valor) {
  return `R$ ${Number(valor).toFixed(2).replace(".", ",")}`;
}

async function verificarSessaoAdmin() {
  try {
    const resp = await fetch(`${API_URL}/api/session`, { credentials: "include" });
    const data = await resp.json();
    if (!resp.ok || data.role !== "admin") {
      window.location.href = "login-admin.html";
    }
  } catch (err) {
    window.location.href = "login-admin.html";
  }
}

async function carregarResumoUnidades() {
  const resp = await fetch(`${API_URL}/api/admin/unidades-resumo`, { credentials: "include" });
  const data = await resp.json();
  const corpo = document.getElementById("corpo-unidades");
  const unidades = data.unidades || [];

  corpo.innerHTML = unidades.map((u) => `
    <tr>
      <td>${u.unidade}</td>
      <td>${u.total_alunos}</td>
      <td>${u.indicacoes_confirmadas}</td>
      <td>${u.indicacoes_pendentes}</td>
    </tr>
  `).join("") || '<tr><td colspan="4">Nenhuma unidade encontrada.</td></tr>';

  filtroUnidade.innerHTML = '<option value="">Todas as unidades</option>' +
    unidades.map((u) => `<option value="${u.unidade_id}">${u.unidade}</option>`).join("");
}

async function carregarPendentes() {
  const resp = await fetch(`${API_URL}/api/admin/indicacoes?status=pendente`, { credentials: "include" });
  const data = await resp.json();
  const corpo = document.getElementById("corpo-pendentes");
  const pendentes = data.indicacoes || [];

  if (!pendentes.length) {
    corpo.innerHTML = '<tr><td colspan="5">Nenhuma indicação pendente.</td></tr>';
    return;
  }

  corpo.innerHTML = pendentes.map((i) => `
    <tr id="linha-${i.id}">
      <td>${i.aluno_nome}</td>
      <td>${i.unidade}</td>
      <td>${i.nome_indicado}</td>
      <td>${i.criado_em}</td>
      <td>
        <button class="btn btn-outline btn-pequeno" data-acao="confirmar" data-id="${i.id}">Confirmar</button>
        <button class="btn btn-outline btn-pequeno" data-acao="rejeitar" data-id="${i.id}">Rejeitar</button>
      </td>
    </tr>
  `).join("");

  corpo.querySelectorAll("button[data-acao]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const acao = btn.dataset.acao;
      btn.disabled = true;
      try {
        await fetch(`${API_URL}/api/admin/indicacoes/${id}/${acao}`, {
          method: "POST", credentials: "include",
        });
        document.getElementById(`linha-${id}`).remove();
        carregarResumoUnidades();
        carregarAlunos();
      } catch (err) {
        btn.disabled = false;
      }
    });
  });
}

async function carregarAlunos() {
  const unidadeId = filtroUnidade.value;
  const url = unidadeId
    ? `${API_URL}/api/admin/alunos?unidade_id=${unidadeId}`
    : `${API_URL}/api/admin/alunos`;
  const resp = await fetch(url, { credentials: "include" });
  const data = await resp.json();
  const corpo = document.getElementById("corpo-alunos");
  const alunos = data.alunos || [];

  corpo.innerHTML = alunos.map((a) => `
    <tr>
      <td>${a.nome}</td>
      <td>${a.cpf}</td>
      <td>${a.unidade}</td>
      <td>${a.total_cliques}</td>
      <td>${a.total_indicacoes_confirmadas}</td>
      <td>${formatarMoeda(a.saldo)}</td>
    </tr>
  `).join("") || '<tr><td colspan="6">Nenhum aluno encontrado.</td></tr>';
}

filtroUnidade.addEventListener("change", carregarAlunos);

btnSair.addEventListener("click", async () => {
  try {
    await fetch(`${API_URL}/api/logout`, { method: "POST", credentials: "include" });
  } catch (err) {}
  sessionStorage.clear();
  window.location.href = "unidade.html";
});

(async function iniciar() {
  await verificarSessaoAdmin();
  await carregarResumoUnidades();
  await carregarPendentes();
  await carregarAlunos();
})();
