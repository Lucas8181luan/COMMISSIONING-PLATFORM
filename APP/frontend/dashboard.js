const selectPolo = document.getElementById("select-polo");
const cardAcoes = document.getElementById("card-acoes");
const tituloPolo = document.getElementById("titulo-polo");
const btnAtualizar = document.getElementById("btn-atualizar");
const btnBaixar = document.getElementById("btn-baixar");
const btnBaixarExcel = document.getElementById("btn-baixar-excel");
const btnBaixarEnccejaonly = document.getElementById("btn-baixar-enccejaonly");
const btnWhatsappRelatorio = document.getElementById("btn-whatsapp-relatorio");
const btnSair = document.getElementById("btn-sair");
const statusBox = document.getElementById("status-box");
const painelVisual = document.getElementById("painel-visual");
const kpiGrid = document.getElementById("kpi-grid");
const btnBaixarPainel = document.getElementById("btn-baixar-painel");
const btnWhatsappPainel = document.getElementById("btn-whatsapp-painel");
const painelCapturavel = document.getElementById("painel-capturavel");
const painelLoading = document.getElementById("painel-loading");
const painelHeader = document.querySelector(".painel-header");
const progressAtualizar = document.getElementById("progress-atualizar");
const alertaBox = document.getElementById("alerta-inatividade");

let poloAtual = "";
let graficos = {};

const CORES = ["#00E5FF", "#00B8CC", "#4DD0E1", "#80DEEA", "#26C6DA", "#0097A7", "#B2EBF2", "#00838F"];

function setStatus(msg, tipo) {
  statusBox.textContent = msg;
  statusBox.className = "status-box" + (tipo ? " " + tipo : "");
}

async function verificarSessao() {
  try {
    const resp = await fetch(`${API_URL}/api/session`, { credentials: "include" });
    if (!resp.ok) {
      window.location.href = "index.html";
      return false;
    }
    return true;
  } catch (err) {
    window.location.href = "index.html";
    return false;
  }
}

async function carregarPolos() {
  const logado = await verificarSessao();
  if (!logado) return;

  try {
    const resp = await fetch(`${API_URL}/api/polos`, { credentials: "include" });
    const data = await resp.json();

    selectPolo.innerHTML = '<option value="">Selecione um polo...</option>';
    (data.polos || []).forEach((polo) => {
      const opt = document.createElement("option");
      opt.value = polo.id;
      opt.textContent = polo.nome;
      selectPolo.appendChild(opt);
    });
  } catch (err) {
    selectPolo.innerHTML = '<option value="">Erro ao carregar polos</option>';
  }
}
carregarPolos();

function destruirGraficos() {
  Object.values(graficos).forEach((g) => g && g.destroy());
  graficos = {};
}

function renderKpis(dados) {
  const cards = (dados.extras || []).filter((e) => e.label);

  kpiGrid.innerHTML = cards.map((c) => `
    <div class="kpi-card">
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-valor">${c.valor}</div>
    </div>
  `).join("");
}

function renderAlerta(dados) {
  const alerta = dados.alerta;
  if (!alerta || !alerta.ativo) {
    alertaBox.style.display = "none";
    return;
  }
  alertaBox.textContent = `Atenção: já se passaram ${alerta.dias_sem_inscricao} dias sem nenhuma nova inscrição (última inscrição em ${alerta.ultima_data}).`;
  alertaBox.style.display = "flex";
}

function abrirModalDetalhes(item) {
  const overlay = document.getElementById("modal-overlay");
  const titulo = document.getElementById("modal-titulo");
  const canvas = document.getElementById("modal-chart");

  titulo.textContent = `Detalhamento — ${item.label}`;

  if (graficos.modal) {
    graficos.modal.destroy();
    graficos.modal = null;
  }

  const detalhes = [...item.detalhes].sort((a, b) => b.valor - a.valor);

  graficos.modal = new Chart(canvas, {
    type: "bar",
    data: {
      labels: detalhes.map((d) => d.label),
      datasets: [{
        label: "Inscrições",
        data: detalhes.map((d) => d.valor),
        backgroundColor: "#00E5FF",
      }],
    },
    options: {
      responsive: true,
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9a9a9a" }, grid: { color: "#1a1a1a" }, beginAtZero: true },
        y: { ticks: { color: "#fff", font: { size: 11 } }, grid: { color: "#1a1a1a" } },
      },
    },
  });

  overlay.classList.add("ativo");
}

function fecharModalDetalhes() {
  const overlay = document.getElementById("modal-overlay");
  overlay.classList.remove("ativo");
  if (graficos.modal) {
    graficos.modal.destroy();
    graficos.modal = null;
  }
}

document.getElementById("modal-fechar").addEventListener("click", fecharModalDetalhes);
document.getElementById("modal-overlay").addEventListener("click", (e) => {
  if (e.target.id === "modal-overlay") fecharModalDetalhes();
});

function criarPizza(canvasId, itens, tipo) {
  const ctx = document.getElementById(canvasId);
  if (!itens || itens.length === 0) return null;
  return new Chart(ctx, {
    type: tipo || "pie",
    data: {
      labels: itens.map((i) => i.label),
      datasets: [{
        data: itens.map((i) => i.valor),
        backgroundColor: itens.map((_, idx) => CORES[idx % CORES.length]),
        borderColor: "#0a0a0a",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      onClick: (evt, elementos) => {
        if (!elementos.length) return;
        const item = itens[elementos[0].index];
        if (item && item.detalhes && item.detalhes.length) {
          abrirModalDetalhes(item);
        }
      },
      onHover: (evt, elementos) => {
        evt.native.target.style.cursor = elementos.length ? "pointer" : "default";
      },
      plugins: {
        legend: { position: "right", labels: { color: "#fff", boxWidth: 12, font: { size: 11 } } },
      },
    },
  });
}

function criarBarras(canvasId, itens) {
  const ctx = document.getElementById(canvasId);
  if (!itens || itens.length === 0) return null;
  return new Chart(ctx, {
    type: "bar",
    data: {
      labels: itens.map((i) => i.label),
      datasets: [{
        label: "Inscrições",
        data: itens.map((i) => i.valor),
        backgroundColor: "#00E5FF",
      }],
    },
    options: {
      responsive: true,
      onClick: (evt, elementos) => {
        if (!elementos.length) return;
        const item = itens[elementos[0].index];
        if (item && item.detalhes && item.detalhes.length) {
          abrirModalDetalhes(item);
        }
      },
      onHover: (evt, elementos) => {
        evt.native.target.style.cursor = elementos.length ? "pointer" : "default";
      },
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { ticks: { color: "#9a9a9a", font: { size: 10 } }, grid: { color: "#1a1a1a" } },
        y: { ticks: { color: "#9a9a9a" }, grid: { color: "#1a1a1a" }, beginAtZero: true },
      },
    },
  });
}

async function carregarPainelVisual() {
  if (!poloAtual) return;

  painelVisual.style.display = "block";
  painelLoading.classList.add("ativo");
  painelHeader.style.display = "none";
  painelCapturavel.style.display = "none";

  try {
    const resp = await fetch(`${API_URL}/api/dashboard-visual?polo=${encodeURIComponent(poloAtual)}`, {
      credentials: "include",
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      painelVisual.style.display = "none";
      alertaBox.style.display = "none";
      return;
    }

    const dados = data.dados;
    renderKpis(dados);
    renderAlerta(dados);
    destruirGraficos();
    graficos.data = criarBarras("chart-data", dados.por_data);
    graficos.local = criarPizza("chart-local", dados.por_local, "pie");
    graficos.cursos = criarBarras("chart-cursos", dados.cursos);

    painelHeader.style.display = "flex";
    painelCapturavel.style.display = "block";
  } catch (err) {
    painelVisual.style.display = "none";
  } finally {
    painelLoading.classList.remove("ativo");
  }
}

// Compartilha um Blob via WhatsApp: usa Web Share API (com arquivo) quando o navegador
// suporta (principalmente celular); no desktop, faz o download e abre o WhatsApp Web
// com uma mensagem, já que não é possível anexar arquivo direto por link.
async function compartilharArquivoWhatsapp(blob, nomeArquivo, mimeType, textoMensagem) {
  const arquivo = new File([blob], nomeArquivo, { type: mimeType });

  if (navigator.canShare && navigator.canShare({ files: [arquivo] })) {
    try {
      await navigator.share({
        files: [arquivo],
        title: nomeArquivo,
        text: textoMensagem,
      });
      return;
    } catch (err) {
      if (err.name === "AbortError") return;
    }
  }

  // Fallback: baixa o arquivo e abre o WhatsApp Web com uma mensagem pronta
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeArquivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);

  const texto = encodeURIComponent(`${textoMensagem}\n\n(O arquivo "${nomeArquivo}" foi baixado — anexe ele na conversa do WhatsApp)`);
  window.open(`https://wa.me/?text=${texto}`, "_blank");
}

selectPolo.addEventListener("change", () => {
  poloAtual = selectPolo.value;
  if (!poloAtual) {
    cardAcoes.style.display = "none";
    painelVisual.style.display = "none";
    alertaBox.style.display = "none";
    return;
  }
  const nomePolo = selectPolo.options[selectPolo.selectedIndex].textContent;
  tituloPolo.textContent = `Relatório — ${nomePolo}`;
  cardAcoes.style.display = "block";
  btnBaixar.disabled = true;
  btnBaixarExcel.disabled = true;
  btnWhatsappRelatorio.disabled = true;
  btnBaixarEnccejaonly.disabled = true;
  btnBaixarEnccejaonly.style.display = (poloAtual === "movimenta") ? "inline-flex" : "none";
  setStatus('Clique em "Atualizar dados" para começar.');
  carregarPainelVisual();
});

btnAtualizar.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnAtualizar.disabled = true;
  btnBaixar.disabled = true;
  btnBaixarExcel.disabled = true;
  btnWhatsappRelatorio.disabled = true;
  progressAtualizar.classList.add("ativo");
  setStatus("Atualizando dados a partir da planilha... isso pode levar alguns minutos.");

  try {
    const resp = await fetch(`${API_URL}/api/atualizar?polo=${encodeURIComponent(poloAtual)}`, {
      method: "POST",
      credentials: "include",
    });
    const data = await resp.json();

    if (!resp.ok || !data.ok) {
      setStatus("Erro ao atualizar: " + (data.erro || "tente novamente."), "erro");
      btnAtualizar.disabled = false;
      return;
    }

    setStatus(
      `Dados atualizados com sucesso — ${data.locais} locais, ${data.meses} meses (${data.atualizado_em}).`,
      "sucesso"
    );
    btnBaixar.disabled = false;
    btnBaixarExcel.disabled = false;
    btnWhatsappRelatorio.disabled = false;
    btnBaixarEnccejaonly.disabled = false;
    carregarPainelVisual();
  } catch (err) {
    setStatus("Não foi possível conectar ao servidor.", "erro");
  } finally {
    btnAtualizar.disabled = false;
    progressAtualizar.classList.remove("ativo");
  }
});

btnBaixar.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnBaixar.disabled = true;
  setStatus("Gerando PDF...");

  try {
    const resp = await fetch(`${API_URL}/api/baixar-pdf?polo=${encodeURIComponent(poloAtual)}`, {
      credentials: "include",
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setStatus("Erro ao gerar PDF: " + (data.erro || "tente novamente."), "erro");
      btnBaixar.disabled = false;
      return;
    }

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `RELACAO_DE_LEADS_${poloAtual.toUpperCase()}_DASHBOARD.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setStatus("PDF baixado com sucesso.", "sucesso");
  } catch (err) {
    setStatus("Não foi possível conectar ao servidor.", "erro");
  } finally {
    btnBaixar.disabled = false;
  }
});

btnBaixarEnccejaonly.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnBaixarEnccejaonly.disabled = true;
  setStatus("Gerando PDF (ENCCEJA)...");

  try {
    const resp = await fetch(`${API_URL}/api/baixar-pdf?polo=${encodeURIComponent(poloAtual)}&responsavel=ENCCEJA`, {
      credentials: "include",
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setStatus("Erro ao gerar PDF: " + (data.erro || "tente novamente."), "erro");
      btnBaixarEnccejaonly.disabled = false;
      return;
    }

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `RELACAO_DE_LEADS_${poloAtual.toUpperCase()}_ENCCEJA_DASHBOARD.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setStatus("PDF (ENCCEJA) baixado com sucesso.", "sucesso");
  } catch (err) {
    setStatus("Não foi possível conectar ao servidor.", "erro");
  } finally {
    btnBaixarEnccejaonly.disabled = false;
  }
});

btnBaixarExcel.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnBaixarExcel.disabled = true;
  setStatus("Gerando Excel...");

  try {
    const resp = await fetch(`${API_URL}/api/baixar-excel?polo=${encodeURIComponent(poloAtual)}`, {
      credentials: "include",
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setStatus("Erro ao gerar Excel: " + (data.erro || "tente novamente."), "erro");
      btnBaixarExcel.disabled = false;
      return;
    }

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `RELACAO_DE_LEADS_${poloAtual.toUpperCase()}_DASHBOARD.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setStatus("Excel baixado com sucesso.", "sucesso");
  } catch (err) {
    setStatus("Não foi possível conectar ao servidor.", "erro");
  } finally {
    btnBaixarExcel.disabled = false;
  }
});

btnWhatsappRelatorio.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnWhatsappRelatorio.disabled = true;
  const htmlOriginal = btnWhatsappRelatorio.innerHTML;
  btnWhatsappRelatorio.textContent = "Preparando...";

  try {
    const resp = await fetch(`${API_URL}/api/baixar-pdf?polo=${encodeURIComponent(poloAtual)}`, {
      credentials: "include",
    });
    if (!resp.ok) throw new Error("Falha ao gerar PDF");

    const blob = await resp.blob();
    const nomePolo = selectPolo.options[selectPolo.selectedIndex]?.textContent || poloAtual;
    await compartilharArquivoWhatsapp(
      blob,
      `RELACAO_DE_LEADS_${poloAtual.toUpperCase()}_DASHBOARD.pdf`,
      "application/pdf",
      `Relatório de Leads — ${nomePolo}`
    );
  } catch (err) {
    alert("Não foi possível preparar o relatório para compartilhar.");
  } finally {
    btnWhatsappRelatorio.disabled = false;
    btnWhatsappRelatorio.innerHTML = htmlOriginal;
  }
});

btnSair.addEventListener("click", async () => {
  await fetch(`${API_URL}/api/logout`, { method: "POST", credentials: "include" });
  window.location.href = "index.html";
});

async function gerarPdfDoPainel() {
  const canvas = await html2canvas(painelCapturavel, {
    backgroundColor: "#0a0a0a",
    scale: 2,
    useCORS: true,
  });

  const imgData = canvas.toDataURL("image/png");
  const { jsPDF } = window.jspdf;

  const larguraPx = canvas.width;
  const alturaPx = canvas.height;
  const larguraMm = 297;
  const alturaMm = (alturaPx * larguraMm) / larguraPx;

  const pdf = new jsPDF({
    orientation: "landscape",
    unit: "mm",
    format: [larguraMm, alturaMm],
  });

  pdf.addImage(imgData, "PNG", 0, 0, larguraMm, alturaMm);
  return pdf.output("blob");
}

btnBaixarPainel.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnBaixarPainel.disabled = true;
  const textoOriginal = btnBaixarPainel.textContent;
  btnBaixarPainel.textContent = "Gerando PDF...";

  try {
    const blob = await gerarPdfDoPainel();
    const nomePolo = selectPolo.options[selectPolo.selectedIndex]?.textContent || poloAtual;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `PAINEL_${nomePolo.toUpperCase().replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert("Não foi possível gerar o PDF do painel. Tente novamente.");
  } finally {
    btnBaixarPainel.disabled = false;
    btnBaixarPainel.textContent = textoOriginal;
  }
});

btnWhatsappPainel.addEventListener("click", async () => {
  if (!poloAtual) return;
  btnWhatsappPainel.disabled = true;
  const htmlOriginal = btnWhatsappPainel.innerHTML;
  btnWhatsappPainel.textContent = "Preparando...";

  try {
    const blob = await gerarPdfDoPainel();
    const nomePolo = selectPolo.options[selectPolo.selectedIndex]?.textContent || poloAtual;
    await compartilharArquivoWhatsapp(
      blob,
      `PAINEL_${nomePolo.toUpperCase().replace(/\s+/g, "_")}.pdf`,
      "application/pdf",
      `Painel de Resultados — ${nomePolo}`
    );
  } catch (err) {
    alert("Não foi possível preparar o painel para compartilhar.");
  } finally {
    btnWhatsappPainel.disabled = false;
    btnWhatsappPainel.innerHTML = htmlOriginal;
  }
});
