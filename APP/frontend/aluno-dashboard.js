const btnSair = document.getElementById("btn-sair");
const btnCopiar = document.getElementById("btn-copiar");
const copiarMsg = document.getElementById("copiar-msg");

function formatarMoeda(valor) {
  return `R$ ${Number(valor).toFixed(2).replace(".", ",")}`;
}

function statusLabel(status) {
  const mapa = { pendente: "Pendente", confirmada: "Confirmada", rejeitada: "Rejeitada" };
  return mapa[status] || status;
}

async function carregarPerfil() {
  try {
    const resp = await fetch(`${API_URL}/api/aluno/perfil`, { credentials: "include" });
    if (!resp.ok) {
      window.location.href = "unidade.html";
      return;
    }
    const data = await resp.json();
    const aluno = data.aluno;

    document.getElementById("aluno-nome").textContent = aluno.nome;
    document.getElementById("aluno-unidade").textContent = `Unidade: ${aluno.unidade}`;
    document.getElementById("kpi-cliques").textContent = aluno.total_cliques;
    document.getElementById("kpi-confirmadas").textContent = aluno.total_indicacoes_confirmadas;
    document.getElementById("kpi-desconto").textContent = formatarMoeda(aluno.desconto_mensalidade);
    document.getElementById("kpi-saldo").textContent = formatarMoeda(aluno.saldo);
    document.getElementById("link-afiliado").value = aluno.link_afiliado;

    const corpo = document.getElementById("corpo-indicacoes");
    if (!aluno.indicacoes.length) {
      corpo.innerHTML = '<tr><td colspan="3">Você ainda não tem indicações.</td></tr>';
    } else {
      corpo.innerHTML = aluno.indicacoes.map((i) => `
        <tr>
          <td>${i.nome_indicado}</td>
          <td><span class="badge badge-${i.status}">${statusLabel(i.status)}</span></td>
          <td>${i.criado_em || "—"}</td>
        </tr>
      `).join("");
    }
  } catch (err) {
    window.location.href = "unidade.html";
  }
}

btnCopiar.addEventListener("click", async () => {
  const input = document.getElementById("link-afiliado");
  try {
    await navigator.clipboard.writeText(input.value);
    copiarMsg.textContent = "Link copiado!";
    copiarMsg.className = "erro-msg sucesso";
  } catch (err) {
    input.select();
    document.execCommand("copy");
    copiarMsg.textContent = "Link copiado!";
    copiarMsg.className = "erro-msg sucesso";
  }
  setTimeout(() => { copiarMsg.textContent = ""; }, 2500);
});

btnSair.addEventListener("click", async () => {
  try {
    await fetch(`${API_URL}/api/logout`, { method: "POST", credentials: "include" });
  } catch (err) {}
  sessionStorage.clear();
  window.location.href = "unidade.html";
});

carregarPerfil();
