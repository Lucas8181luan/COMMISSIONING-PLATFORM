"""
dashboard_eduthree.py
Lógica do polo EDUTHREE: agrupa por LOCAL + CURSO, recria as abas
e a DASHBOARD (mesma lógica do seu script original do polo Eduthree).

Colocar em: APP/backend/dashboard_eduthree.py  (arquivo NOVO)
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

SPREADSHEET_ID = "1abhr3M3FBNOeXKopdEd_Z7O40th4EwW2x4MtECgQOe4"
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

COR_AMARELO_ESCURO = {"red": 1.000, "green": 0.851, "blue": 0.302}
COR_AMARELO_CLARO = {"red": 1.000, "green": 0.953, "blue": 0.651}
COR_HEADER = {"red": 0.741, "green": 0.584, "blue": 0.000}
COR_MES_HEADER = {"red": 0.25, "green": 0.25, "blue": 0.25}
COR_MES_ATUAL = {"red": 0.13, "green": 0.37, "blue": 0.13}


def make_tab_title(local: str, curso: str) -> str:
    title = f"{local} - {curso}" if curso else local
    return sanitize_sheet_name(title)


def build_data_inicio(registros: list) -> str:
    for row in registros:
        if len(row) > COL_DATA_INICIO:
            val = row[COL_DATA_INICIO].strip()
            if val:
                return val
    return ''


def cleanup_sheets(spreadsheet):
    keep = {ORIGIN_SHEET_NAME.upper(), "DADOS", "DASHBOARD"}
    to_delete = [ws for ws in spreadsheet.worksheets() if ws.title.strip().upper() not in keep]
    for ws in to_delete:
        try:
            spreadsheet.del_worksheet(ws)
            time.sleep(1.5)
        except Exception:
            pass


def create_tab(spreadsheet, title: str):
    sanitized = sanitize_sheet_name(title)
    for ws in spreadsheet.worksheets():
        if ws.title.strip().upper() == sanitized.strip().upper():
            spreadsheet.del_worksheet(ws)
            time.sleep(1.5)
            break
    sheet = retry_api_call(lambda: spreadsheet.add_worksheet(title=sanitized, rows=1000, cols=11))
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


def _create_dashboard(spreadsheet, combos_dict: dict):
    COLS_FIXAS = 7
    today = agora_brasilia()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    all_dates = []
    for registros in combos_dict.values():
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
    total_cols = COLS_FIXAS + n_meses
    total_cols_sheet = total_cols + COL_OFFSET
    mes_atual_ym = (today.year, today.month)
    mes_atual_idx = meses.index(mes_atual_ym) if mes_atual_ym in meses else -1

    contagem_mensal = {}
    for combo_key, registros in combos_dict.items():
        contagem_mensal[combo_key] = defaultdict(int)
        for row in registros:
            d = parse_date(row[COL_DATA])
            if d:
                contagem_mensal[combo_key][(d.year, d.month)] += 1

    sheet = _get_or_create_dashboard_sheet(spreadsheet, min_cols=total_cols_sheet + 2)

    def col_letter(idx):
        return rowcol_to_a1(1, idx).rstrip('1')

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

    headers_fixos = ['LOCAL', 'CURSO', 'DATA DE INÍCIO', 'TOTAL', 'TOTAL NO MÊS',
                      'DIA ANTERIOR', 'ÚLTIMA SEMANA']
    headers = headers_fixos + [mes_label(y, m) for y, m in meses]
    retry_api_call(lambda: sheet.update(f"B1:{col_letter(total_cols_sheet)}1", [headers]))

    dashboard_data = []
    for (local, curso), registros in combos_dict.items():
        total = len(registros)
        y_count = w_count = m_count = 0
        for row in registros:
            d = parse_date(row[COL_DATA]) if len(row) > COL_DATA else None
            if d:
                if d.date() == yesterday.date():
                    y_count += 1
                if d.date() >= week_ago.date():
                    w_count += 1
                if month_start.date() <= d.date() <= today.date():
                    m_count += 1
        data_inicio_str = build_data_inicio(registros)
        mensais = [contagem_mensal[(local, curso)].get(ym, 0) for ym in meses]
        dashboard_data.append({
            'local': local, 'curso': curso, 'data_inicio_str': data_inicio_str,
            'total': total, 'm_count': m_count, 'y_count': y_count, 'w_count': w_count,
            'mensais': mensais,
        })

    dashboard_data.sort(key=lambda x: (x['local'].upper(), x['curso'].upper()))

    rows_out = [
        [d['local'], d['curso'], d['data_inicio_str'], d['total'], d['m_count'],
         d['y_count'], d['w_count']] + d['mensais']
        for d in dashboard_data
    ]

    if rows_out:
        chunk_size = 50
        for i in range(0, len(rows_out), chunk_size):
            chunk = rows_out[i:i + chunk_size]
            ec = col_letter(total_cols_sheet)
            retry_api_call(lambda c=chunk, idx=i, e=ec: sheet.update(f"B{idx+2}:{e}{idx+len(c)+1}", c))
            time.sleep(1)

    total_row = len(rows_out) + 2
    O = COL_OFFSET

    # Totais calculados em Python (igual ao Movimenta) — não são fórmulas do Sheets
    soma_total = sum(row[3] for row in rows_out)
    soma_mes = sum(row[4] for row in rows_out)
    soma_dia_anterior = sum(row[5] for row in rows_out)
    soma_semana = sum(row[6] for row in rows_out)
    somas_meses = [sum(row[7 + i] for row in rows_out) for i in range(n_meses)]
    total_locais = len(rows_out)

    linha_total = ['TOTAL', total_locais, '', soma_total, soma_mes, soma_dia_anterior, soma_semana] + somas_meses
    retry_api_call(lambda: sheet.update(f"B{total_row}:{col_letter(total_cols_sheet)}{total_row}", [linha_total]))

    time.sleep(2)
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
    ]

    if mes_atual_idx >= 0:
        col_idx = O + COLS_FIXAS + mes_atual_idx
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 1,
            "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
            "cell": {"userEnteredFormat": {"backgroundColor": COR_MES_ATUAL,
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}})

    for i in range(len(rows_out)):
        bg = COR_AMARELO_ESCURO if i % 2 == 0 else COR_AMARELO_CLARO
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": i + 1, "endRowIndex": i + 2,
            "startColumnIndex": O, "endColumnIndex": O + COLS_FIXAS}, "cell": {"userEnteredFormat": {"backgroundColor": bg}},
            "fields": "userEnteredFormat(backgroundColor)"}})
        bg_mes = {k: min(1.0, v * 0.3 + 0.7) for k, v in bg.items()}
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

    return len(rows_out), n_meses


def atualizar_dashboard():
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    cleanup_sheets(spreadsheet)

    origin = spreadsheet.worksheet(ORIGIN_SHEET_NAME)
    all_values = origin.get_all_values()
    data_rows = all_values[1:] if all_values else []

    combos_dict = {}
    for row in data_rows:
        local = row[COL_LOCAL].strip() if len(row) > COL_LOCAL else ''
        curso = row[COL_CURSO].strip() if len(row) > COL_CURSO else ''
        if local:
            combos_dict.setdefault((local, curso), []).append(row)

    for (local, curso), registros in combos_dict.items():
        title = make_tab_title(local, curso)
        sheet = create_tab(spreadsheet, title)
        new_rows = []
        for r in registros:
            row = list(r)
            while len(row) < 11:
                row.append('')
            new_rows.append(row[:11])
        if new_rows:
            chunk_size = 100
            for i in range(0, len(new_rows), chunk_size):
                chunk = new_rows[i:i + chunk_size]
                retry_api_call(lambda c=chunk, s=sheet, i=i: s.update(f"A{i+2}:K{i+len(c)+1}", c))
            time.sleep(1)

    n_combos, n_meses = _create_dashboard(spreadsheet, combos_dict)
    return {
        "ok": True,
        "locais": n_combos,
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
