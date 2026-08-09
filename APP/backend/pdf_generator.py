"""
pdf_generator.py
Gera o PDF do relatório (RELAÇÃO DE LEADS - MOVIMENTA - DASHBOARD)
a partir dos dados já lidos da aba DASHBOARD.

Colocar em: APP/backend/pdf_generator.py  (SUBSTITUI o anterior)
"""

import io
from datetime import datetime
from gsheet_client import agora_brasilia
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

CIANO = colors.HexColor("#00E5FF")
PRETO = colors.HexColor("#0B0B0B")
BRANCO = colors.white
COBALTO = colors.HexColor("#3D8BFF")

_wrap_style = ParagraphStyle(
    "CelulaComQuebra", fontName="Helvetica", fontSize=6, leading=7.5,
    textColor=colors.black, alignment=TA_LEFT, wordWrap="CJK",
)


def _aplicar_quebra_linha(data_tabela: list, headers: list, colunas_alvo: set) -> list:
    """Converte o texto de colunas específicas (por nome do cabeçalho) em Paragraph,
    para que nomes longos de LOCAL/CURSO quebrem em várias linhas em vez de
    sobrepor a linha da tabela."""
    indices = {i for i, h in enumerate(headers) if h.strip().upper() in colunas_alvo}
    if not indices:
        return data_tabela
    nova_tabela = [data_tabela[0]]
    for row in data_tabela[1:]:
        primeiro_valor = str(row[0]).strip().upper() if row else ""
        if primeiro_valor.startswith("TOTAL"):
            nova_tabela.append(row)
            continue
        nova_linha = list(row)
        for i in indices:
            if i < len(nova_linha) and nova_linha[i]:
                texto = str(nova_linha[i]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                nova_linha[i] = Paragraph(texto, _wrap_style)
        nova_tabela.append(nova_linha)
    return nova_tabela

RESP_COLORS_PDF = {
    "CHARBEL":   colors.Color(0.678, 0.847, 0.902),
    "CRISTIANE": colors.Color(0.714, 0.902, 0.714),
    "ENCCEJA":   colors.Color(1.000, 0.949, 0.667),
    "OUTRO":     colors.Color(1.000, 0.800, 0.800),
}
COR_SEM_TURMA = colors.Color(0.800, 0.400, 0.400)
COR_COM_TURMA = colors.Color(0.550, 0.780, 0.550)


def gerar_pdf_dashboard(headers: list, rows: list) -> bytes:
    buffer = io.BytesIO()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TituloRelatorio", parent=styles["Heading1"],
        fontSize=14, textColor=PRETO, alignment=TA_LEFT, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "SubRelatorio", parent=styles["Normal"],
        fontSize=9, textColor=colors.grey, spaceAfter=10,
    )

    n_cols = max(len(headers), 1)
    largura_total = max(297 * mm, 60 * mm + n_cols * 16 * mm)
    margem_topo_rodape = 40 * mm
    altura_titulo = 24 * mm

    if not rows:
        doc = SimpleDocTemplate(
            buffer, pagesize=(largura_total, 210 * mm),
            leftMargin=8 * mm, rightMargin=8 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        )
        elementos = [
            Paragraph("RELAÇÃO DE LEADS — MOVIMENTA RIO — DASHBOARD", title_style),
            Paragraph(f"Gerado em {agora_brasilia().strftime('%d/%m/%Y %H:%M')}", sub_style),
            Paragraph("Nenhum dado encontrado na aba DASHBOARD.", styles["Normal"]),
        ]
        doc.build(elementos)
        return buffer.getvalue()

    data_tabela = _aplicar_quebra_linha([headers] + rows, headers, {"LOCAL"})

    largura_disponivel = largura_total - 16 * mm
    larguras = []
    for i in range(n_cols):
        if i == 1:
            larguras.append(largura_disponivel * 0.22)
        elif i == 0:
            larguras.append(largura_disponivel * 0.07)
        elif i == 6:
            larguras.append(largura_disponivel * 0.07)
        elif i == 7:
            larguras.append(largura_disponivel * 0.06)
        else:
            resto = largura_disponivel * 0.58
            n_resto = max(n_cols - 4, 1)
            larguras.append(resto / n_resto)

    tabela = Table(data_tabela, colWidths=larguras, repeatRows=1)

    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), PRETO),
        ("TEXTCOLOR", (0, 0), (-1, 0), CIANO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 6),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    status_col = 7 if len(headers) > 7 and headers[7].strip().upper() == "STATUS" else None
    resp_col = 0 if len(headers) > 0 and headers[0].strip().upper() == "RESPONSÁVEL" else None

    for idx, row in enumerate(rows, start=1):
        primeiro_valor = str(row[0]).strip().upper() if row else ""
        eh_linha_total = primeiro_valor.startswith("TOTAL")
        if eh_linha_total:
            estilo.append(("BACKGROUND", (0, idx), (-1, idx), PRETO))
            estilo.append(("TEXTCOLOR", (0, idx), (-1, idx), CIANO))
            estilo.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
            estilo.append(("FONTSIZE", (0, idx), (-1, idx), 7))
            estilo.append(("ALIGN", (1, idx), (1, idx), "CENTER"))
            estilo.append(("FONTNAME", (0, idx), (0, idx), "Helvetica-BoldOblique"))
            continue

        if resp_col is not None and len(row) > resp_col:
            cor = RESP_COLORS_PDF.get(row[resp_col].strip().upper(), colors.white)
            fim_col_fixa = (status_col - 1) if status_col is not None else (len(headers) - 1)
            estilo.append(("BACKGROUND", (0, idx), (fim_col_fixa, idx), cor))
            if status_col is not None:
                estilo.append(("BACKGROUND", (status_col + 1, idx), (-1, idx), cor))

        if status_col is not None and len(row) > status_col:
            status_val = row[status_col].strip().upper()
            cor_status = COR_SEM_TURMA if status_val == "SEM TURMA" else COR_COM_TURMA
            estilo.append(("BACKGROUND", (status_col, idx), (status_col, idx), cor_status))
            estilo.append(("TEXTCOLOR", (status_col, idx), (status_col, idx), BRANCO))
            estilo.append(("FONTNAME", (status_col, idx), (status_col, idx), "Helvetica-Bold"))

    tabela.setStyle(TableStyle(estilo))

    # Mede a altura real da tabela (já considerando quebras de linha nos nomes longos)
    _, altura_tabela_real = tabela.wrap(largura_disponivel, 100000 * mm)
    altura_total = margem_topo_rodape + altura_titulo + altura_tabela_real + 15 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(largura_total, altura_total),
        leftMargin=8 * mm, rightMargin=8 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
    )

    elementos = [
        Paragraph("RELAÇÃO DE LEADS — MOVIMENTA RIO — DASHBOARD", title_style),
        Paragraph(f"Gerado em {agora_brasilia().strftime('%d/%m/%Y %H:%M')}", sub_style),
        tabela,
    ]

    doc.build(elementos)
    return buffer.getvalue()


def _reordenar_colunas(headers: list, rows: list, ordem_desejada: list):
    """Reordena colunas pelo nome do cabeçalho. Colunas não citadas em ordem_desejada
    (ex: os meses) ficam no final, na ordem original."""
    indices = []
    usados = set()
    for nome in ordem_desejada:
        for i, h in enumerate(headers):
            if i not in usados and h.strip().upper() == nome.strip().upper():
                indices.append(i)
                usados.add(i)
                break
    for i in range(len(headers)):
        if i not in usados:
            indices.append(i)

    novos_headers = [headers[i] for i in indices]
    novas_rows = [[r[i] if i < len(r) else '' for i in indices] for r in rows]
    return novos_headers, novas_rows


def gerar_pdf_generico(headers: list, rows: list, titulo: str,
                        cor_header_hex: str, cor_par_rgb: tuple, cor_impar_rgb: tuple) -> bytes:
    """Gerador de PDF genérico para polos que usam alternância de cor por linha
    (Fortaleza — vermelho, Eduthree — dourado/amarelo), em vez de cor por responsável."""
    buffer = io.BytesIO()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TituloRelatorio", parent=styles["Heading1"],
        fontSize=14, textColor=PRETO, alignment=TA_LEFT, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "SubRelatorio", parent=styles["Normal"],
        fontSize=9, textColor=colors.grey, spaceAfter=10,
    )

    n_cols = max(len(headers), 1)
    largura_total = max(297 * mm, 60 * mm + n_cols * 16 * mm)
    margem_topo_rodape = 40 * mm
    altura_titulo = 24 * mm

    if not rows:
        doc = SimpleDocTemplate(
            buffer, pagesize=(largura_total, 210 * mm),
            leftMargin=8 * mm, rightMargin=8 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        )
        elementos = [
            Paragraph(titulo, title_style),
            Paragraph(f"Gerado em {agora_brasilia().strftime('%d/%m/%Y %H:%M')}", sub_style),
            Paragraph("Nenhum dado encontrado na aba DASHBOARD.", styles["Normal"]),
        ]
        doc.build(elementos)
        return buffer.getvalue()

    data_tabela = _aplicar_quebra_linha([headers] + rows, headers, {"LOCAL", "CURSO", "CURSOS", "DATA DE INÍCIO"})
    largura_disponivel = largura_total - 16 * mm
    larguras = []
    colunas_largas = {"TOTAL INSCRIÇÕES", "DIA ANTERIOR", "ÚLTIMA SEMANA"}
    colunas_especiais = {"LOCAL": 0.20, "CURSOS": 0.16, "CURSO": 0.16, "DATA DE INÍCIO": 0.13}
    n_largas = sum(1 for h in headers if h.strip().upper() in colunas_largas)
    n_especiais = sum(1 for h in headers if h.strip().upper() in colunas_especiais)
    n_resto = max(n_cols - n_largas - n_especiais, 1)
    largura_resto_total = largura_disponivel * (1 - 0.20 - 0.16 - 0.13 - 0.11 * n_largas)
    for i in range(n_cols):
        nome_col = headers[i].strip().upper() if i < len(headers) else ""
        if nome_col in colunas_especiais:
            larguras.append(largura_disponivel * colunas_especiais[nome_col])
        elif nome_col in colunas_largas:
            larguras.append(largura_disponivel * 0.11)
        else:
            larguras.append(max(largura_resto_total, largura_disponivel * 0.05) / n_resto)

    tabela = Table(data_tabela, colWidths=larguras, repeatRows=1)
    cor_header = colors.HexColor(cor_header_hex)
    cor_par = colors.Color(*cor_par_rgb)
    cor_impar = colors.Color(*cor_impar_rgb)

    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), cor_header),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 6),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for idx, row in enumerate(rows, start=1):
        linha_vazia = not any(str(c).strip() for c in row)
        primeiro_valor = str(row[0]).strip().upper() if row else ""
        eh_linha_total = (linha_vazia and idx == len(rows)) or primeiro_valor.startswith("TOTAL")
        if eh_linha_total:
            estilo.append(("BACKGROUND", (0, idx), (-1, idx), PRETO))
            estilo.append(("TEXTCOLOR", (0, idx), (-1, idx), CIANO))
            estilo.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
            estilo.append(("FONTSIZE", (0, idx), (-1, idx), 7))
            estilo.append(("ALIGN", (1, idx), (1, idx), "CENTER"))
            estilo.append(("FONTNAME", (0, idx), (0, idx), "Helvetica-BoldOblique"))
            continue
        cor_linha = cor_par if (idx - 1) % 2 == 0 else cor_impar
        estilo.append(("BACKGROUND", (0, idx), (-1, idx), cor_linha))

    tabela.setStyle(TableStyle(estilo))

    # Mede a altura real da tabela (já considerando quebras de linha nos nomes longos)
    _, altura_tabela_real = tabela.wrap(largura_disponivel, 100000 * mm)
    altura_total = margem_topo_rodape + altura_titulo + altura_tabela_real + 15 * mm

    doc = SimpleDocTemplate(
        buffer, pagesize=(largura_total, altura_total),
        leftMargin=8 * mm, rightMargin=8 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
    )

    elementos = [
        Paragraph(titulo, title_style),
        Paragraph(f"Gerado em {agora_brasilia().strftime('%d/%m/%Y %H:%M')}", sub_style),
        tabela,
    ]

    doc.build(elementos)
    return buffer.getvalue()


def gerar_pdf_fortaleza(headers: list, rows: list) -> bytes:
    ordem = ['LOCAL', 'CURSOS', 'TOTAL INSCRIÇÕES', 'DIA ANTERIOR', 'ÚLTIMA SEMANA', 'DATA DE INÍCIO']
    headers, rows = _reordenar_colunas(headers, rows, ordem)
    return gerar_pdf_generico(
        headers, rows, "RELAÇÃO DE LEADS — FORTALEZA — DASHBOARD",
        cor_header_hex="#000000",
        cor_par_rgb=(0.808, 0.224, 0.224),
        cor_impar_rgb=(0.957, 0.741, 0.741),
    )


def gerar_pdf_eduthree(headers: list, rows: list) -> bytes:
    return gerar_pdf_generico(
        headers, rows, "RELAÇÃO DE LEADS — EDUTHREE — DASHBOARD",
        cor_header_hex="#BD9500",
        cor_par_rgb=(1.000, 0.851, 0.302),
        cor_impar_rgb=(1.000, 0.953, 0.651),
    )
