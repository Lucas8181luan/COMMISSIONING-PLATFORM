"""
dashboard_fortaleza.py
Lógica do polo FORTALEZA: recria as abas por local + DASHBOARD
(mesma lógica do seu script original do polo Fortaleza).

Colocar em: APP/backend/dashboard_fortaleza.py  (arquivo NOVO)
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict

import gspread
from gspread.utils import rowcol_to_a1

from gsheet_client import (
    get_gsheet_client, retry_api_call, sanitize_sheet_name,
    parse_date, mes_label, gerar_meses, analisar_dados_visual, agora_brasilia,
)

SPREADSHEET_ID = "1_xIjtNB3NIJzrbTsUkNd8PbVtMh7US0d2URi_UssFZc"
ORIGIN_SHEET_NAME = "DADOS"

COL_DATA = 0
COL_GENERO = 3
COL_CURSO = 4
COL_LOCAL = 8
COL_DATA_INICIO = 9

HEADERS = [
    'DATA', 'NOME', 'CPF', 'GÊNERO', 'CURSO', 'WHATSAPP',
    'CEP', 'EMAIL', 'LOCAL DO CURSO', 'DATA DE INÍCIO', 'HORÁRIO'
]

COR_VERMELHO_ESCURO = {"red": 0.808, "green": 0.224, "blue": 0.224}
COR_VERMELHO_CLARO = {"red": 0.957, "green": 0.741, "blue": 0.741}
COR_HEADER = {"red": 0.0, "green": 0.0, "blue": 0.0}
COR_MES_HEADER = {"red": 0.25, "green": 0.25, "blue": 0.25}
COR_MES_ATUAL = {"red": 0.13, "green": 0.37, "blue": 0.13}


def build_data_inicio_str(registros: list) -> str:
    curso_data = {}
    for row in registros:
        curso = row[COL_CURSO].strip() if len(row) > COL_CURSO else ''
        data = row[COL_DATA_INICIO].strip() if len(row) > COL_DATA_INICIO else ''
        if data and curso not in curso_data:
            curso_data[curso] = data
    if not curso_data:
        return ''
    datas_unicas = list(dict.fromkeys(curso_data.values()))
    if len(datas_unicas) == 1:
        return datas_unicas[0]
    return " | ".join(f"{curso}: {data}" for curso, data in curso_data.items() if data)


def cleanup_sheets(spreadsheet):
    keep = {ORIGIN_SHEET_NAME.upper(), "DADOS"}
    to_delete = [ws for ws in spreadsheet.worksheets() if ws.title.strip().upper() not in keep]
    for ws in to_delete:
        try:
            spreadsheet.del_worksheet(ws)
            time.sleep(1.5)
        except Exception:
            pass


def filter_by_local(spreadsheet, local_name):
    sanitized = sanitize_sheet_name(local_name)
    for ws in spreadsheet.worksheets():
        if ws.title.strip().upper() == sanitized.strip().upper():
            spreadsheet.del_worksheet(ws)
            time.sleep(1.5)
            break
    sheet = retry_api_call(lambda: spreadsheet.add_worksheet(title=sanitized, rows=1000, cols=len(HEADERS)))
    retry_api_call(lambda: sheet.update('A1:K1', [HEADERS]))
    return sheet


COL_OFFSET = 1  # coluna A reservada/preservada (uso manual do usuário)


def _get_or_create_dashboard_sheet(spreadsheet, min_cols: int, min_rows: int = 2000):
    try:
        sheet = spreadsheet.worksheet("DASHBOARD")
        if sheet.col_count < min_cols:
            retry_api_call(lambda: sheet.resize(cols=min_cols))
        if sheet.row_count < min_rows:
            retry_api_call(lambda: sheet.resize(rows=min_rows))
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        return retry_api_call(lambda: spreadsheet.add_worksheet(title="DASHBOARD", rows=min_rows, cols=min_cols))


def _create_dashboard(spreadsheet, locals_dict):
    COLS_FIXAS = 6
    today = agora_brasilia()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    all_dates = []
    for registros in locals_dict.values():
        for row in registros:
            d = parse_date(row[COL_DATA])
            if d:
                all_dates.append(d.date())

    if all_dates:
        min_ym = (min(all_dates).year, min(all_dates).month)
        max_ym = (max(all_dates).year, max(all_dates).month)
    else:
        min_ym = max_ym = (today.year, today.month)

    meses = gerar_meses(min_ym, max_ym)
    n_meses = len(meses)
    total_cols = COLS_FIXAS + n_meses            # colunas de conteúdo (a partir da coluna B)
    total_cols_sheet = total_cols + COL_OFFSET     # total incluindo a coluna A reservada
    mes_atual_ym = (today.year, today.month)
    mes_atual_idx = meses.index(mes_atual_ym) if mes_atual_ym in meses else -1

    contagem_mensal = {}
    for local_name, registros in locals_dict.items():
        contagem_mensal[local_name] = defaultdict(int)
        for row in registros:
            d = parse_date(row[COL_DATA])
            if d:
                contagem_mensal[local_name][(d.year, d.month)] += 1

    sheet = _get_or_create_dashboard_sheet(spreadsheet, min_cols=total_cols_sheet + 2)

    def col_letter(idx):
        return rowcol_to_a1(1, idx).rstrip('1')

    # Limpa somente as colunas B em diante (preserva a coluna A), valores e formatação
    ultima_col_letra = col_letter(total_cols_sheet + 5)
    retry_api_call(lambda: sheet.batch_clear([f"B1:{ultima_col_letra}3000"]))
    time.sleep(1)
    retry_api_call(lambda: spreadsheet.batch_update({"requests": [{
        "repeatCell": {
            "range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 3000,
                       "startColumnIndex": 1, "endColumnIndex": total_cols_sheet + 5},
            "cell": {"userEnteredFormat": {}}, "fields": "userEnteredFormat"
        }
    }]}))

    headers_fixos = ['LOCAL', 'CURSOS', 'DATA DE INÍCIO', 'TOTAL INSCRIÇÕES',
                      'DIA ANTERIOR', 'ÚLTIMA SEMANA']
    headers = headers_fixos + [mes_label(y, m) for y, m in meses]
    retry_api_call(lambda: sheet.update(f"B1:{col_letter(total_cols_sheet)}1", [headers]))

    dashboard_data = []
    for local_name, registros in locals_dict.items():
        total = len(registros)
        yesterday_cnt = 0
        week_cnt = 0
        cursos_vistos = []
        for row in registros:
            curso = row[COL_CURSO].strip() if len(row) > COL_CURSO else ''
            if curso and curso not in cursos_vistos:
                cursos_vistos.append(curso)
            if len(row) > COL_DATA:
                d = parse_date(row[COL_DATA])
                if d:
                    if d.date() == yesterday.date():
                        yesterday_cnt += 1
                    if d.date() >= week_ago.date():
                        week_cnt += 1
        cursos_str = " | ".join(cursos_vistos) if cursos_vistos else ''
        data_inicio_str = build_data_inicio_str(registros)
        mensais = [contagem_mensal[local_name].get(ym, 0) for ym in meses]
        dashboard_data.append(
            [local_name, cursos_str, data_inicio_str, total, yesterday_cnt, week_cnt] + mensais
        )

    dashboard_data.sort(key=lambda x: x[0].upper())

    if dashboard_data:
        chunk_size = 50
        for i in range(0, len(dashboard_data), chunk_size):
            chunk = dashboard_data[i:i + chunk_size]
            ec = col_letter(total_cols_sheet)
            retry_api_call(lambda c=chunk, idx=i, e=ec: sheet.update(f"B{idx+2}:{e}{idx+len(c)+1}", c))
            time.sleep(1)

    total_row = len(dashboard_data) + 2
    O = COL_OFFSET

    # Totais calculados em Python (igual ao Movimenta) — não são fórmulas do Sheets
    soma_total = sum(row[3] for row in dashboard_data)
    soma_dia_anterior = sum(row[4] for row in dashboard_data)
    soma_semana = sum(row[5] for row in dashboard_data)
    somas_meses = [sum(row[6 + i] for row in dashboard_data) for i in range(n_meses)]
    total_locais = len(dashboard_data)

    linha_total = ['TOTAL', total_locais, '', soma_total, soma_dia_anterior, soma_semana] + somas_meses
    retry_api_call(lambda: sheet.update(f"B{total_row}:{col_letter(total_cols_sheet)}{total_row}", [linha_total]))

    time.sleep(2)
    n_rows = len(dashboard_data)
    fmt = [
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 1,
            "startColumnIndex": O, "endColumnIndex": O + COLS_FIXAS},
            "cell": {"userEnteredFormat": {"backgroundColor": COR_HEADER,
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 1,
            "startColumnIndex": O + COLS_FIXAS, "endColumnIndex": O + total_cols},
            "cell": {"userEnteredFormat": {"backgroundColor": COR_MES_HEADER,
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": total_row - 1, "endRowIndex": total_row,
            "startColumnIndex": O, "endColumnIndex": O + total_cols},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0},
                "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.898, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sheet.id,
            "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 3}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
        # Coluna LOCAL bem mais larga, com quebra de linha para caber o nome inteiro
        {"updateDimensionProperties": {"range": {"sheetId": sheet.id, "dimension": "COLUMNS",
            "startIndex": O, "endIndex": O + 1}, "properties": {"pixelSize": 420}, "fields": "pixelSize"}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 1, "endRowIndex": total_row,
            "startColumnIndex": O, "endColumnIndex": O + 1},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
        # Coluna DATA DE INÍCIO bem mais larga, com quebra de linha
        {"updateDimensionProperties": {"range": {"sheetId": sheet.id, "dimension": "COLUMNS",
            "startIndex": O + 2, "endIndex": O + 3}, "properties": {"pixelSize": 260}, "fields": "pixelSize"}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 1, "endRowIndex": total_row,
            "startColumnIndex": O + 2, "endColumnIndex": O + 3},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
        # Colunas TOTAL INSCRIÇÕES, DIA ANTERIOR e ÚLTIMA SEMANA mais largas
        {"updateDimensionProperties": {"range": {"sheetId": sheet.id, "dimension": "COLUMNS",
            "startIndex": O + 3, "endIndex": O + 6}, "properties": {"pixelSize": 150}, "fields": "pixelSize"}},
    ]

    if mes_atual_idx >= 0:
        col_idx = O + COLS_FIXAS + mes_atual_idx
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 1,
            "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
            "cell": {"userEnteredFormat": {"backgroundColor": COR_MES_ATUAL,
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}})

    for i in range(n_rows):
        bg = COR_VERMELHO_ESCURO if i % 2 == 0 else COR_VERMELHO_CLARO
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": i + 1, "endRowIndex": i + 2,
            "startColumnIndex": O, "endColumnIndex": O + COLS_FIXAS}, "cell": {"userEnteredFormat": {"backgroundColor": bg}},
            "fields": "userEnteredFormat(backgroundColor)"}})
        bg_mes = {k: min(1.0, v * 0.35 + 0.65) for k, v in bg.items()}
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": i + 1, "endRowIndex": i + 2,
            "startColumnIndex": O + COLS_FIXAS, "endColumnIndex": O + total_cols}, "cell": {"userEnteredFormat": {"backgroundColor": bg_mes}},
            "fields": "userEnteredFormat(backgroundColor)"}})

    retry_api_call(lambda: spreadsheet.batch_update({"requests": fmt}))
    retry_api_call(lambda: spreadsheet.batch_update({"requests": [{
        "repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 1, "endRowIndex": total_row - 1,
            "startColumnIndex": O, "endColumnIndex": O + 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}}, "fields": "userEnteredFormat(textFormat)"}
    }]}))

    # Reforço final: limpa validação de dados residual e deixa "TOTAL" em itálico (igual ao Movimenta)
    retry_api_call(lambda: spreadsheet.batch_update({"requests": [
        {"setDataValidation": {"range": {"sheetId": sheet.id, "startRowIndex": total_row - 1, "endRowIndex": total_row,
            "startColumnIndex": O, "endColumnIndex": O + total_cols}}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": total_row - 1, "endRowIndex": total_row,
            "startColumnIndex": O, "endColumnIndex": O + 1},
            "cell": {"userEnteredFormat": {"textFormat": {"italic": True, "bold": True}}},
            "fields": "userEnteredFormat(textFormat)"}},
    ]}))

    return len(dashboard_data), n_meses


def atualizar_dashboard():
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    cleanup_sheets(spreadsheet)

    origin = spreadsheet.worksheet(ORIGIN_SHEET_NAME)
    all_values = origin.get_all_values()
    data_rows = all_values[1:] if all_values else []

    locals_dict = {}
    for row in data_rows:
        if len(row) > COL_LOCAL:
            local = row[COL_LOCAL].strip()
            if local:
                locals_dict.setdefault(local, []).append(row)

    for local_name, registros in locals_dict.items():
        sheet_name = sanitize_sheet_name(local_name)
        new_sheet = filter_by_local(spreadsheet, sheet_name)
        rows_to_insert = []
        for row in registros:
            r = list(row)
            while len(r) < 11:
                r.append('')
            rows_to_insert.append(r[:11])
        if rows_to_insert:
            chunk_size = 100
            for i in range(0, len(rows_to_insert), chunk_size):
                chunk = rows_to_insert[i:i + chunk_size]
                retry_api_call(lambda c=chunk, s=new_sheet, i=i: s.update(f"A{i+2}:K{i+len(c)+1}", c))
            time.sleep(1)

    n_locais, n_meses = _create_dashboard(spreadsheet, locals_dict)
    return {
        "ok": True,
        "locais": n_locais,
        "meses": n_meses,
        "atualizado_em": agora_brasilia().strftime('%d/%m/%Y %H:%M:%S'),
    }


def ler_dashboard_atual():
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.worksheet("DASHBOARD")
    values = sheet.get_all_values()
    if not values:
        return {"headers": [], "rows": []}
    headers = values[0][COL_OFFSET:]
    corpo = [r[COL_OFFSET:] for r in values[1:]]

    ultima_com_dado = -1
    for i, r in enumerate(corpo):
        if len(r) > 0 and r[0].strip():
            ultima_com_dado = i

    if ultima_com_dado == -1:
        return {"headers": headers, "rows": []}

    limite = min(ultima_com_dado + 2, len(corpo))
    return {"headers": headers, "rows": corpo[:limite]}


def obter_dashboard_visual():
    """Monta os KPIs e dados de gráficos (estilo QualificaTech) a partir da aba DADOS."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return analisar_dados_visual(spreadsheet, COL_DATA, COL_GENERO, COL_CURSO, COL_LOCAL,
                                  origin_sheet_name=ORIGIN_SHEET_NAME)
