"""
gsheet_client.py
Conexão com o Google Sheets compartilhada por todos os polos.

Colocar em: APP/backend/gsheet_client.py  (arquivo NOVO)
"""

import os
import json
import time
import gspread
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def agora_brasilia() -> datetime:
    """Data/hora atual no fuso de Brasília (o servidor roda em UTC)."""
    return datetime.now(FUSO_BRASILIA)


def get_gsheet_client():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        creds_path = os.environ.get("GOOGLE_SHEETS_CREDS", "credentials.json")
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)


def retry_api_call(func, max_retries=12, base_delay=5):
    import requests.exceptions
    TRANSIENT = (
        requests.exceptions.ReadTimeout,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ConnectionError,
    )
    for attempt in range(max_retries):
        try:
            return func()
        except gspread.exceptions.APIError as e:
            if '429' in str(e):
                time.sleep(base_delay * (2 ** attempt))
            else:
                raise
        except TRANSIENT:
            time.sleep(base_delay * (2 ** attempt))
    return func()


def sanitize_sheet_name(name: str) -> str:
    if not name:
        return "Local_Sem_Nome"
    name = str(name)[:100]
    for ch in ['\\', '/', '*', '?', ':', '[', ']']:
        name = name.replace(ch, '_')
    name = ' '.join(name.split())
    if not name or name.isdigit():
        name = "Local_" + name
    return name.strip()


def parse_date(date_str: str):
    from datetime import datetime
    if not date_str or not date_str.strip():
        return None
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            pass
    return None


MESES_PT = {
    1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
    7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'
}


def mes_label(year: int, month: int) -> str:
    return f"{MESES_PT[month]}/{str(year)[-2:]}"


def gerar_meses(min_ym, max_ym):
    meses = []
    y, m = min_ym
    while (y, m) <= max_ym:
        meses.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return meses


def analisar_dados_visual(spreadsheet, col_data, col_genero, col_curso, col_local,
                           origin_sheet_name="DADOS", top_n=10):
    """Lê a aba DADOS e monta os números para o painel visual (estilo QualificaTech):
    KPIs, gráfico de sexo, inscrições por data, inscrições por local, cursos escolhidos.
    Também lê os KPIs extras manuais nas colunas M:P (linha 1 = rótulo, linha 2 = valor),
    se existirem."""
    from collections import Counter
    from datetime import datetime as dt

    origin = spreadsheet.worksheet(origin_sheet_name)
    valores = origin.get_all_values()
    linhas = valores[1:] if valores else []

    total = len(linhas)
    hoje = agora_brasilia().date()
    leads_hoje = 0

    contagem_genero = Counter()
    contagem_data = Counter()
    contagem_local = Counter()
    contagem_curso = Counter()

    for row in linhas:
        d = parse_date(row[col_data]) if len(row) > col_data else None
        if d:
            if d.date() == hoje:
                leads_hoje += 1
            contagem_data[d.strftime('%d/%m')] += 1

        genero = row[col_genero].strip() if len(row) > col_genero and row[col_genero].strip() else 'Não informado'
        contagem_genero[genero] += 1

        curso = row[col_curso].strip() if len(row) > col_curso and row[col_curso].strip() else 'Não informado'
        contagem_curso[curso] += 1

        local = row[col_local].strip() if len(row) > col_local and row[col_local].strip() else 'Não informado'
        contagem_local[local] += 1

    def _top(counter, n):
        itens_top = counter.most_common(n)
        restantes = counter.most_common()[n:]
        outros_total = sum(v for _, v in restantes)
        resultado = [{"label": k, "valor": v} for k, v in itens_top]
        if outros_total > 0:
            detalhes = [{"label": k, "valor": v} for k, v in restantes]
            resultado.append({"label": "Outros", "valor": outros_total, "detalhes": detalhes})
        return resultado

    datas_ordenadas = sorted(contagem_data.items(), key=lambda kv: dt.strptime(kv[0], '%d/%m'))
    por_data = [{"label": k, "valor": v} for k, v in datas_ordenadas]

    # Alerta: 2 dias ou mais sem nenhuma inscrição nova (compara com a última data real na coluna A)
    todas_datas = []
    for row in linhas:
        d = parse_date(row[col_data]) if len(row) > col_data else None
        if d:
            todas_datas.append(d.date())
    alerta = {"ativo": False, "dias_sem_inscricao": 0, "ultima_data": None}
    if todas_datas:
        ultima_data = max(todas_datas)
        dias_sem = (hoje - ultima_data).days
        alerta = {
            "ativo": dias_sem >= 2,
            "dias_sem_inscricao": dias_sem,
            "ultima_data": ultima_data.strftime('%d/%m/%Y'),
        }

    # KPIs extras manuais (colunas M:P — TOTAL DE LEADS, MATRÍCULAS FEITAS, ALUNOS EM TURMA, MATRÍCULAS DE HOJE)
    extras = []
    try:
        bloco = origin.get('M1:P2')
        if bloco and len(bloco) >= 2:
            rotulos = bloco[0]
            valores_extra = bloco[1]
            for i in range(len(rotulos)):
                v = valores_extra[i] if i < len(valores_extra) else ''
                extras.append({"label": rotulos[i], "valor": v})
    except Exception:
        pass

    return {
        "sexo": [{"label": k, "valor": v} for k, v in contagem_genero.most_common()],
        "por_data": por_data,
        "por_local": _top(contagem_local, top_n),
        "cursos": _top(contagem_curso, top_n),
        "extras": extras,
        "alerta": alerta,
    }
