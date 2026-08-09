"""
dashboard_movimenta.py
Lógica de negócio: conecta no Google Sheets, recria a aba DASHBOARD
(mesma lógica do seu script original) e permite ler os dados atuais
da aba DASHBOARD para gerar o PDF.

Colocar em: APP/backend/dashboard_movimenta.py  (renomeie/substitua o antigo dashboard_data.py)
"""

import os
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from gsheet_client import analisar_dados_visual, agora_brasilia

SPREADSHEET_ID = "1XcXcSNA4WYvVHqCQztCo4E-vIyohmZXE14QFFnx7l3Q"
ORIGIN_SHEET_NAME = "DADOS"

COL_DATA = 0
COL_GENERO = 3
COL_CURSO = 4
COL_LOCAL = 8

HEADERS = [
    'DATA', 'NOME', 'CPF', 'GÊNERO', 'CURSO', 'WHATSAPP',
    'CEP', 'EMAIL', 'LOCAL DO CURSO', 'DATA DE INÍCIO', 'HORÁRIO'
]

MESES_PT = {
    1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
    7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'
}

SEM_TURMA = {
    'VILA SÃO JORGE - COSMOS',
    'IARAQUÃ - CAMPO GRANDE',
    'CÂNDIDO MAGALHÃES - CAMPO GRANDE',
    'CONJUNTO HABITACIONAL/ASSOCIAÇÃO DE MORADORES BENTO RIBEIRO DANTAS - MARÉ',
    'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA - GUARATIBA',
}

DATAS_INICIO_FIXAS = {
    'AMUBUA (ASSOCIAÇÃO) - SANTA CRUZ': '02/06/2026',
    'ASSEMBLEIA DE DEUS ADTS DE COLÉGIO - COLÉGIO': '22/06/2026',
    'ASSEMBLEIA DE DEUS ADTS MANDELA - BENFICA': '13/07/2026',
    'ASSEMBLEIA DE DEUS NA PAVUNA - COSMOS': '18/05/2026',
    'ASSOCIAÇÃO AMIGOS DO BARATA - REALENGO': '08/06/2026',
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)': '16/05/2026',
    'ASSOCIAÇÃO DOS ARTESÃOS - ANA GONZAGA': '03/06/2026',
    'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE - SANTA CRUZ': '13/06/2026',
    'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS': '25/05/2026',
    'CENTRO CULTURAL LOTTUS - MEIER': '08/06/2026',
    'CENTRO SOCIAL ESTRELA DA MANHÃ - GUARATIBA': '19/05/2026',
    'COZINHA COMUNITÁRIA - REALENGO': '26/05/2026',
    'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)': '11/04/2026',
    'IG. ASS. DE DEUS RESG. VALORES - ARNALDO EUGÊNIO': '27/03/2026',
    'IGREJA BATISTA DE COLÉGIO - COLÉGIO': '19/05/2026',
    'IGREJA BATISTA DO MANDELA - BENIFICA': '29/05/2026',
    'IGREJA BATISTA EBENEZER - INHOAÍBA': '11/05/2026',
    'IGREJA BATISTA MAANAIM MENDANHA - CAMPO GRANDE': '23/05/2026',
    'IGREJA BATISTA RIO DE PRATA - BANGU': '01/06/2026',
    'IGREJA BATISTA SÃO BENTO - BANGU (SÃO BENTO)': '06/06/2026',
    'IGREJA EVANGÉLICA PÃO DA VIDA - CURICICA': '18/05/2026',
    'IGREJA METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE (RIO DA PRATA)': '30/05/2026',
    'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL': '30/05/2026',
    'IMMEC CHURCH - CAMPO GRANDE': '01/06/2026',
    'MINISTÉRIO APOSTÓLICO MOVER PROFÉTICO - SENADOR CAMARÁ': '10/06/2026',
    'MINISTÉRIO APOSTÓLICO TENDA DO ENCONTRO - COSMOS': '02/06/2026',
    'PREFEITURA - ALFONSO CAVALCANTI': '03/06/2026',
    'QUADRA UNIDOS DE MANGUINHOS - MANGUINHOS': '26/05/2026',
    'REFORÇO ESCOLAR TIA DANI - MARÉ': '06/06/2026',
    'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) - MENDANHA': '30/05/2026',
    'SALÃO DE FESTAS - PADRE MIGUEL': '08/06/2026',
    'SALÃO DE FESTAS ENCANTOS MIL - SANTA CRUZ': '16/05/2026',
    'TIA LU - REALENGO': '06/05/2026',
    'VILA CRUZEIRO - PENHA': '23/05/2026',
    'VILA DO PINHEIRO - MARÉ': '02/06/2026',
    'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA - GUARATIBA': '08/06/2026',
    'ASSEMBLÉIA DE DEUS MINISTÉRIO ROCHA': '03/08/2026',
    'CABLOCOS - CAMPO GRANDE': '08/06/2026',
    'CABUÇU DE BAIXO': '08/06/2026',
    'CAJU - SALA 01': '10/08/2026',
    'CAJU': '10/08/2026',
    'CONJUNTO HABITACIONAL/ASSOCIAÇÃO DE MORADORES BENTO RIBEIRO DANTAS - MARÉ': '25/05/2026',
    'CÂNDIDO MAGALHÃES - CAMPO GRANDE': '25/05/2026',
    'ESTRADA CORONEL VIEIRA - IRAJÁ': '11/05/2026',
    'GUADALUPE': '04/05/2026',
    'IARAQUÃ - CAMPO GRANDE': '30/04/2026',
    'MARÉ 1 - RUA CAPITÃO CARLOS (BONSUCESSO)': '25/05/2026',
    'MARÉ 2 - RUA CAPITÃO CARLOS (BONSUCESSO)': '25/05/2026',
    'NÚCLEO PENHA - JOSUÉ ARANHA': '08/06/2026',
    'NÚCLEO PRAÇA SECA - PRAÇA SECA': '08/06/2026',
    'PADRE MANSO - MADUREIRA': '11/05/2026',
    'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE': '08/06/2026',
    'RIO GRANDE - JACAREPAGUÁ': '11/05/2026',
    'URUCÂNIA - SANTA CRUZ': '25/05/2026',
    'VILA SÃO JORGE - COSMOS': '11/05/2026',
    'ASSOCIAÇÃO AMUBUA - SANTA CRUZ': '18/05/2026',
    'CASA COSTA MATOS - REALENGO': '25/05/2026',
    'IGREJA ASSEMBLÉIA DE DEUS - COLÉGIO': '25/05/2026',
    'IGREJA BATISTA MAANAIM MENDANHA - ENCCEJA': '18/05/2026',
    'IGREJA BATISTA VIDA E ESPERANÇA - BANGU': '16/05/2026',
}

CURSO_ENCCEJA = '📑 PREPARATÓRIO ENCCEJA 2026'
LOCAL_MAANAIM = 'IGREJA BATISTA MAANAIM MENDANHA - CAMPO GRANDE'
LOCAL_MAANAIM_ENCCEJA = 'IGREJA BATISTA MAANAIM MENDANHA - ENCCEJA'

LOCAL_INHOAIBA = '__INHOAIBA__'
LOCAL_INHOAIBA_EBENEZER = 'IGREJA BATISTA EBENEZER - INHOAÍBA'
LOCAL_INHOAIBA_ASSOC = 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)'
CURSOS_INHOAIBA_EBENEZER: list = []

LOCAL_COSMOS = '__COSMOS__'
LOCAL_COSMOS_ASSEMBLEIA = 'ASSEMBLEIA DE DEUS NA PAVUNA - COSMOS'
LOCAL_COSMOS_TENDA = 'MINISTÉRIO APOSTÓLICO TENDA DO ENCONTRO - COSMOS'
CURSOS_COSMOS_TENDA: list = []

CHARBEL_LOCAIS = [
    'AMUBUA (ASSOCIAÇÃO) - SANTA CRUZ', LOCAL_COSMOS_ASSEMBLEIA,
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DOS ARTESÃOS - ANA GONZAGA',
    'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE - SANTA CRUZ',
    'ASSEMBLEIA DE DEUS ADTS DE COLÉGIO - COLÉGIO',
    'ASSEMBLEIA DE DEUS ADTS MANDELA - BENFICA',
    'ASSOCIAÇÃO AMIGOS DO BARATA - REALENGO',
    'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS',
    'CENTRO CULTURAL LOTTUS - MEIER',
    'CENTRO SOCIAL ESTRELA DA MANHÃ - GUARATIBA',
    'COZINHA COMUNITÁRIA - REALENGO',
    'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)',
    'IG. ASS. DE DEUS RESG. VALORES - ARNALDO EUGÊNIO',
    'IGREJA BATISTA DE COLÉGIO - COLÉGIO',
    'IGREJA BATISTA DO MANDELA - BENIFICA',
    LOCAL_INHOAIBA_EBENEZER, LOCAL_MAANAIM,
    'IGREJA BATISTA RIO DE PRATA - BANGU',
    'IGREJA BATISTA SÃO BENTO - BANGU (SÃO BENTO)',
    'IGREJA EVANGÉLICA PÃO DA VIDA - CURICICA',
    'IGREJA METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE (RIO DA PRATA)',
    'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'IMMEC CHURCH - CAMPO GRANDE',
    'MINISTÉRIO APOSTÓLICO MOVER PROFÉTICO - SENADOR CAMARÁ',
    LOCAL_COSMOS_TENDA, 'PREFEITURA - ALFONSO CAVALCANTI',
    'QUADRA UNIDOS DE MANGUINHOS - MANGUINHOS',
    'REFORÇO ESCOLAR TIA DANI - MARÉ',
    'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) - MENDANHA',
    'SALÃO DE FESTAS - PADRE MIGUEL',
    'SALÃO DE FESTAS ENCANTOS MIL - SANTA CRUZ',
    'TIA LU - REALENGO', 'VILA CRUZEIRO - PENHA', 'VILA DO PINHEIRO - MARÉ',
]

CRISTIANE_LOCAIS = [
    'ASSEMBLÉIA DE DEUS MINISTÉRIO ROCHA',
    'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA - GUARATIBA',
    'CABUÇU DE BAIXO', 'CABLOCOS - CAMPO GRANDE', 'CAJU - SALA 01',
    'CÂNDIDO MAGALHÃES - CAMPO GRANDE',
    'CONJUNTO HABITACIONAL/ASSOCIAÇÃO DE MORADORES BENTO RIBEIRO DANTAS - MARÉ',
    'ESTRADA CORONEL VIEIRA - IRAJÁ', 'GUADALUPE', 'IARAQUÃ - CAMPO GRANDE',
    'MARÉ 1 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'MARÉ 2 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'NÚCLEO PENHA - JOSUÉ ARANHA', 'NÚCLEO PRAÇA SECA - PRAÇA SECA',
    'PADRE MANSO - MADUREIRA', 'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE',
    'RIO GRANDE - JACAREPAGUÁ', 'URUCÂNIA - SANTA CRUZ', 'VILA SÃO JORGE - COSMOS',
]

ENCCEJA_LOCAIS = [
    'ASSOCIAÇÃO AMUBUA - SANTA CRUZ', 'CASA COSTA MATOS - REALENGO',
    'IGREJA ASSEMBLÉIA DE DEUS - COLÉGIO', 'IGREJA BATISTA VIDA E ESPERANÇA - BANGU',
    LOCAL_MAANAIM_ENCCEJA,
]

NORMALIZACAO = {
    'ANE KIDS-PRAÇA DO BARRO VERMELHO - SALA 01': 'URUCÂNIA - SANTA CRUZ',
    'ANE KIDS-PRAÇA DO BARRO VERMELHO - SALA 02': 'URUCÂNIA - SANTA CRUZ',
    'ANE KIDS-PRAÇA DO BARRO VERMELHO — SALA 01': 'URUCÂNIA - SANTA CRUZ',
    'ANE KIDS-PRAÇA DO BARRO VERMELHO — SALA 02': 'URUCÂNIA - SANTA CRUZ',
    'ASSEMBLEIA DE DEUS FILIAL MARECHAL HERMES - GUADALUPE': 'GUADALUPE',
    'POLO GUADALUPE - SALA 1': 'GUADALUPE', 'POLO GUADALUPE - SALA 2': 'GUADALUPE',
    'POLO GUADALUPE - SALA 3': 'GUADALUPE', 'POLO GUADALUPE — SALA 1': 'GUADALUPE',
    'POLO GUADALUPE — SALA 2': 'GUADALUPE', 'POLO GUADALUPE — SALA 3': 'GUADALUPE',
    'GUADALUPE — SALA 01': 'GUADALUPE', 'GUADALUPE — SALA 02': 'GUADALUPE',
    'GUADALUPE — SALA 03': 'GUADALUPE', 'MOVIMENTA RIO — GUADALUPE': 'GUADALUPE',
    'R. JOAQUIM SARMENTO, 183': 'GUADALUPE',
    'NÚCLEO PENHA (PROGRAMA JOSÚBE ARANHA)': 'NÚCLEO PENHA - JOSUÉ ARANHA',
    'NÚCLEO PENHA (PROGRAMA JOSÚE ARANHA)': 'NÚCLEO PENHA - JOSUÉ ARANHA',
    'COMUNIDADE EVANGÉLICA CHAMA DO AMOR - CAMPO GRANDE': 'CABLOCOS - CAMPO GRANDE',
    'CABOCLOS - COMUNIDADE EVANGÉLICA CHAMA DO AMOR': 'CABLOCOS - CAMPO GRANDE',
    'CABUÇU DE BAIXO - GUARATIBA': 'CABUÇU DE BAIXO', 'CABUÇU DE BAIXO — GUARATIBA': 'CABUÇU DE BAIXO',
    'CAJU — SALA 01': 'CAJU - SALA 01',
    'ASSOC. AMIGOS DO BARATA — REALENGO': 'ASSOCIAÇÃO AMIGOS DO BARATA - REALENGO',
    'ASSOC. AMIGOS DO BARATA - REALENGO': 'ASSOCIAÇÃO AMIGOS DO BARATA - REALENGO',
    'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA': 'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA - GUARATIBA',
    'AUGUSTO VASCONCELOS - CAMPO GRANDE': 'CABLOCOS - CAMPO GRANDE',
    'CABOCLOS - CAMPO GRANDE': 'CABLOCOS - CAMPO GRANDE',
    'IARAQUA - CAMPO GRANDE': 'IARAQUÃ - CAMPO GRANDE', 'IARAQUÃ — CAMPO GRANDE': 'IARAQUÃ - CAMPO GRANDE',
    'CORONEL VIEIRA - IRAJÁ': 'ESTRADA CORONEL VIEIRA - IRAJÁ',
    'ESTRADA CORONEL VIERA - IRAJÁ': 'ESTRADA CORONEL VIEIRA - IRAJÁ',
    'IRAJÁ': 'ESTRADA CORONEL VIEIRA - IRAJÁ',
    'CONJUNTO HABITACIONAL/ ASSOCIAÇÃO DE MORADORES BENTO RIBEIRO DANTAS - MARÉ':
        'CONJUNTO HABITACIONAL/ASSOCIAÇÃO DE MORADORES BENTO RIBEIRO DANTAS - MARÉ',
    'URUCANIA - SANTA CRUZ': 'URUCÂNIA - SANTA CRUZ', 'URUCÂNIA — SANTA CRUZ': 'URUCÂNIA - SANTA CRUZ',
    'PROESPV, PROJETO ESPERANÇA E VIDA': 'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE',
    'PROJETO ESPERANÇA E VIDA': 'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE',
    'PROESPV - CAMPO GRANDE': 'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE',
    'PROESPV': 'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE',
    'PROESPV - PROJETO ESPERANÇA E VIDA': 'PROJETO ESPERANÇA E VIDA - CAMPO GRANDE',
    'ESTR. DO RIO GRANDE, 4985': 'RIO GRANDE - JACAREPAGUÁ',
    'MADUREIRA': 'PADRE MANSO - MADUREIRA',
    'NÚCLEO XIII - CAMPO GRANDE': 'CÂNDIDO MAGALHÃES - CAMPO GRANDE',
    'PRAÇA SECA': 'NÚCLEO PRAÇA SECA - PRAÇA SECA',
    'IGREJA FONTE DE VIDA ETERNA - PRAÇA SECA': 'NÚCLEO PRAÇA SECA - PRAÇA SECA',
    'IGREJA FONTE DE VIDA ETERNA — PRAÇA SECA': 'NÚCLEO PRAÇA SECA - PRAÇA SECA',
    'IGREJA JARDIM MARAVILHA - GUARATIBA': 'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA - GUARATIBA',
    'IGREJA JARDIM MARAVILHA — GUARATIBA': 'ASSEMBLEIA DE DEUS MINISTÉRIO TERRA RICA - GUARATIBA',
    'POLO MADUREIRA - SALA 1': 'PADRE MANSO - MADUREIRA', 'POLO MADUREIRA - SALA 2': 'PADRE MANSO - MADUREIRA',
    'POLO MADUREIRA — SALA 1': 'PADRE MANSO - MADUREIRA', 'POLO MADUREIRA — SALA 2': 'PADRE MANSO - MADUREIRA',
    'POLO IRAJÁ — SALA 1': 'ESTRADA CORONEL VIEIRA - IRAJÁ',
    'POLO JACAREPAGUÁ — SALA 1': 'RIO GRANDE - JACAREPAGUÁ',
    'MARÉ I': 'MARÉ 1 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'MARÉ 1 — RUA CAPITÃO CARLOS (BONSUCESSO)': 'MARÉ 1 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'MARÉ 1 — RUA CAPITÃO CARLOS — BONSUCESSO': 'MARÉ 1 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'MARÉ II': 'MARÉ 2 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'MARÉ 2 — RUA CAPITÃO CARLOS (BONSUCESSO)': 'MARÉ 2 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'MARÉ 2 — RUA CAPITÃO CARLOS — BONSUCESSO': 'MARÉ 2 - RUA CAPITÃO CARLOS (BONSUCESSO)',
    'CASA COSTA MATOS — RIO DE JANEIRO': 'CASA COSTA MATOS - REALENGO',
    'CASA COSTA MATOS. - REALENGO': 'CASA COSTA MATOS - REALENGO',
    'CASA COSTA MATOS — REALENGO': 'CASA COSTA MATOS - REALENGO',
    'IGREJA ASSEMBLEIA DE DEUS COLÉGIO': 'IGREJA ASSEMBLÉIA DE DEUS - COLÉGIO',
    'IGREJA ASSEMBLEIA DE DEUS - COLÉGIO': 'IGREJA ASSEMBLÉIA DE DEUS - COLÉGIO',
    'ASSOCIAÇÃO AMUBUA': 'ASSOCIAÇÃO AMUBUA - SANTA CRUZ',
    'AD ADTS MANDELA — BENFICA': 'IGREJA BATISTA DO MANDELA - BENIFICA',
    'IG. UNIÃO EVANGÉLICA PENTECOSTAL — COSMOS': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'IG. UNIÃO EVANGÉLICA PENTECOSTAL': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'ASSOC. DE MORADORES SÃO JORGE — INHOAÍBA': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'IG. METODISTA EMBARCADOS C/CRISTO — CAMPO GRANDE': 'IGREJA METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE (RIO DA PRATA)',
    'IG. METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE': 'IGREJA METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE (RIO DA PRATA)',
    'IG. METODISTA EMBARCADOS COM CRISTO - RIO DA PRATA': 'IGREJA METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE (RIO DA PRATA)',
    'IGREJA METODISTA EMBARCADOS COM CRISTO': 'IGREJA METODISTA EMBARCADOS COM CRISTO - CAMPO GRANDE (RIO DA PRATA)',
    'IGREJA BATISTA MAANAIM MENDANHA': LOCAL_MAANAIM, 'IGREJA BATISTA MAANAIM': LOCAL_MAANAIM,
    'IGREJA BATISTA MAANAIM - CAMPO GRANDE': LOCAL_MAANAIM, 'IGREJA BATISTA MAANAIM - MENDANHA': LOCAL_MAANAIM,
    'IGREJA BATISTA MAANAIM MENDANHA - ESTRADA DO MENDANHA': LOCAL_MAANAIM,
    'IGR. BATISTA MAANAIM MENDANHA - CAMPO GRANDE': LOCAL_MAANAIM,
    'IGREJA BATISTA MAANAIM MENDANHA — CAMPO GRANDE': LOCAL_MAANAIM,
    'SALÃO DE FESTAS (77) - PADRE MIGUEL': 'SALÃO DE FESTAS - PADRE MIGUEL',
    'SALÃO DE FESTAS (77) — PADRE MIGUEL': 'SALÃO DE FESTAS - PADRE MIGUEL',
    'SALÃO DE FESTA - PADRE MIGUEL': 'SALÃO DE FESTAS - PADRE MIGUEL',
    'SALÃO DE FESTAS — PADRE MIGUEL': 'SALÃO DE FESTAS - PADRE MIGUEL',
    'SALÃO DE FESTAS ENCANTOS MIL': 'SALÃO DE FESTAS ENCANTOS MIL - SANTA CRUZ',
    'SALÃO DE FESTAS': 'SALÃO DE FESTAS ENCANTOS MIL - SANTA CRUZ',
    'SALÃO DE FESTAS - SANTA CRUZ': 'SALÃO DE FESTAS ENCANTOS MIL - SANTA CRUZ',
    'SALÃO DE FESTAS — SANTA CRUZ': 'SALÃO DE FESTAS ENCANTOS MIL - SANTA CRUZ',
    'ASSOC. MORADORES CONJ. LIBERDADE — SANTA CRUZ': 'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE - SANTA CRUZ',
    'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE': 'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE - SANTA CRUZ',
    'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE — SANTA CRUZ': 'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE - SANTA CRUZ',
    'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE — SANTA CRUZZ': 'ASSOCIAÇÃO MORADORES CONJUNTO LIBERDADE - SANTA CRUZ',
    'ASSOCIAÇÃO DOS ARTESÃOS': 'ASSOCIAÇÃO DOS ARTESÃOS - ANA GONZAGA',
    'ASSOCIAÇÃO DOS ARTESÃOS — ANA GONZAGA': 'ASSOCIAÇÃO DOS ARTESÃOS - ANA GONZAGA',
    'ALCIDES FRANCO - GUARATIBA': 'CENTRO SOCIAL ESTRELA DA MANHÃ - GUARATIBA',
    'CENTRAL SOCIAL ESTRELA DA MANHÃ': 'CENTRO SOCIAL ESTRELA DA MANHÃ - GUARATIBA',
    'CENTRO SOCIAL ESTRELA DA MANHÃ — GUARATIBA': 'CENTRO SOCIAL ESTRELA DA MANHÃ - GUARATIBA',
    'RUA ALCIDES FRANCO, Nº 175': 'CENTRO SOCIAL ESTRELA DA MANHÃ - GUARATIBA',
    'IG. BATISTA EBENEZER - INHOAÍBA': LOCAL_INHOAIBA_EBENEZER, 'IGREJA BATISTA EBENEZER': LOCAL_INHOAIBA_EBENEZER,
    'IGREJA BATISTA EBENEZER - CAMPO GRANDE': LOCAL_INHOAIBA_EBENEZER,
    'IGREJA BATISTA EBENEZER - CAMPO GRANDE (INHOAÍBA)': LOCAL_INHOAIBA_EBENEZER,
    'IGREJA BATISTA EBENEZER - INHOAÍBA': LOCAL_INHOAIBA_EBENEZER,
    'IGREJA BATISTA EBENEZER — INHOAÍBA': LOCAL_INHOAIBA_EBENEZER,
    'IGREJA BATISTA EBENEZER — INHOAIBA': LOCAL_INHOAIBA_EBENEZER,
    'VILA CRUZEIRO — PENHA': 'VILA CRUZEIRO - PENHA',
    'VILA DO PINHEIRO - MARÊ': 'VILA DO PINHEIRO - MARÉ', 'VILA DO PINHEIRO — MARÉ': 'VILA DO PINHEIRO - MARÉ',
    'AD ADTS DE COLÉGIO — COLÉGIO': 'ASSEMBLEIA DE DEUS ADTS DE COLÉGIO - COLÉGIO',
    'ASSEMBLEIA DE DEUS ADTS DE COLÉGIO — COLÉGIO': 'ASSEMBLEIA DE DEUS ADTS DE COLÉGIO - COLÉGIO',
    'RESIDENCIAL RIO SAMBA (CONDOMINIOS) - MENDANHA': 'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) - MENDANHA',
    'RESIDENCIAL RIO SAMBA (CONDOMÍNIO) - MENDANHA': 'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) - MENDANHA',
    'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) — MENDANHA': 'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) - MENDANHA',
    'RESIDENCIAL RIO SAMBA — CAMPO GRANDE': 'RESIDENCIAL RIO SAMBA (CONDOMÍNIOS) - MENDANHA',
    'AD NA PAVUNA — COSMOS': LOCAL_COSMOS_ASSEMBLEIA, 'ASSEMBLEIA DE DEUS NA PAVUNA': LOCAL_COSMOS_ASSEMBLEIA,
    'ASSEMBLEIA DE DEUS NA PAVUNA — COSMOS': LOCAL_COSMOS_ASSEMBLEIA,
    'IGREJA BATISTA RIO DA PRAIA - BANGU': 'IGREJA BATISTA RIO DE PRATA - BANGU',
    'IGREJA BATISTA RIO DA PRATA - BANGU': 'IGREJA BATISTA RIO DE PRATA - BANGU',
    'IGREJA BATISTA RIO DA PRATA — BANGU': 'IGREJA BATISTA RIO DE PRATA - BANGU',
    'IGREJA BATISTA SÃO BENTO - SÃO BENTO-BANGU': 'IGREJA BATISTA SÃO BENTO - BANGU (SÃO BENTO)',
    'IGREJA BATISTA SÃO BENTO - BANGU': 'IGREJA BATISTA SÃO BENTO - BANGU (SÃO BENTO)',
    'IGREJA BATISTA SÃO BENTO — BANGU': 'IGREJA BATISTA SÃO BENTO - BANGU (SÃO BENTO)',
    'IMMEC CHURCH — CAMPO GRANDE': 'IMMEC CHURCH - CAMPO GRANDE', 'IMMEC CHURCH - CAMPO GRANDE': 'IMMEC CHURCH - CAMPO GRANDE',
    'MIN. AP. MOVER PROFÉTICO — SENADOR CAMARÁ': 'MINISTÉRIO APOSTÓLICO MOVER PROFÉTICO - SENADOR CAMARÁ',
    'MINISTÉRIO APOSTÓLICO MOVER PROFÉTICO — SENADOR CAMARÁ': 'MINISTÉRIO APOSTÓLICO MOVER PROFÉTICO - SENADOR CAMARÁ',
    'RUA DARCY VARGAS - MARÉ': 'REFORÇO ESCOLAR TIA DANI - MARÉ', 'RUA DARCY VARGAS - MARÊ': 'REFORÇO ESCOLAR TIA DANI - MARÉ',
    'REFORÇO ESCOLAR TIA DANI — MARÉ': 'REFORÇO ESCOLAR TIA DANI - MARÉ', 'TIA LU — REALENGO': 'TIA LU - REALENGO',
    'HERVAL ROSSANO - COSMOS': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL', 'HERVAL ROSSANO — COSMOS': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'HERVAL ROSSANO - COSMOS - CEP.: 23.066-350': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'RUA HERVAL ROSSANO, LT. 26, QD. 16': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL — COSMOS': 'IGREJA UNIÃO EVANGÉLICA PENTECOSTAL',
    'CENTRO CULTURAL LOTTUS - MÉIER': 'CENTRO CULTURAL LOTTUS - MEIER', 'CENTRO CULTURAL LOTTUS — MÉIER': 'CENTRO CULTURAL LOTTUS - MEIER',
    'CENTRO CULTURAL LOTTUS — MEIER': 'CENTRO CULTURAL LOTTUS - MEIER', 'COZINHA COMUNITÁRIA — REALENGO': 'COZINHA COMUNITÁRIA - REALENGO',
    'ASSOCIAÇÃO AMIGOS DO BARATA — REALENGO': 'ASSOCIAÇÃO AMIGOS DO BARATA - REALENGO',
    'INHOAÍBA': LOCAL_INHOAIBA, 'INHOAIBA': LOCAL_INHOAIBA, 'COSMOS': LOCAL_COSMOS,
    'ASSOC. DE MORADORES SÃO JORGE - INHOAÍBA': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE (INHOAÍBA)': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE — INHOAIBA': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DE MORADORES SÃO JORGE — INHOAÍBA': 'ASSOCIAÇÃO DE MORADORES SÃO JORGE - CAMPO GRANDE (INHOAÍBA)',
    'ASSOCIAÇÃO DE MORADORES VILAR CARIOCA': 'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)',
    'CRECHE TIA ANINHA': 'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)',
    'CRECHE TIA ANINHA - CAMPO GRANDE': 'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)',
    'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CAICOCA)': 'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)',
    'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CAIOCA)': 'CRECHE TIA ANINHA - CAMPO GRANDE (VILAR CARIOCA)',
    'IGREJA EVANGÉLICA PÃO DA VIDA': 'IGREJA EVANGÉLICA PÃO DA VIDA - CURICICA',
    'IGREJA EVANGÉLICA PÃO DA VIDA — CURICICA': 'IGREJA EVANGÉLICA PÃO DA VIDA - CURICICA',
    'CAMPO SOCYTE DE MANGUINHOS': 'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS',
    'CAMPO SOCYTE DE MANGUINHOS — MANGUINHOS': 'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS',
    'CAMPO SOCIETY DE MANGUINHOS': 'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS',
    'CAMPO SOCIETY DE MANGUINHOS - MANGUINHOS': 'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS',
    'CAMPO SOCIETY DE MANGUINHOS — MANGUINHOS': 'CAMPO SOCYTE DE MANGUINHOS - MANGUINHOS',
    'QUADRA UNIDOS DE MANGUINHOS': 'QUADRA UNIDOS DE MANGUINHOS - MANGUINHOS',
    'QUADRA UNIDOS DE MANGUINHOS — MANGUINHOS': 'QUADRA UNIDOS DE MANGUINHOS - MANGUINHOS',
    'MINISTÉRIO APOSTÓLICO TENDA DO ENCONTRO': LOCAL_COSMOS_TENDA,
    'MINISTÉRIO APOSTÓLICO TENDA DO ENCONTRO — COSMOS': LOCAL_COSMOS_TENDA,
    'AMUBUA (ASSOCIAÇÃO)': 'AMUBUA (ASSOCIAÇÃO) - SANTA CRUZ', 'AMUBUA (ASSOCIAÇÃO) — SANTA CRUZ': 'AMUBUA (ASSOCIAÇÃO) - SANTA CRUZ',
    'IG. ASS. DE DEUS RESG, VALORES - ARNALDO EUGÊNIO': 'IG. ASS. DE DEUS RESG. VALORES - ARNALDO EUGÊNIO',
    'IGREJA ASSEMBLEIA DE DEUS RESGATANDO VALORES': 'IG. ASS. DE DEUS RESG. VALORES - ARNALDO EUGÊNIO',
    'PREFEITURA - CENTRO': 'PREFEITURA - ALFONSO CAVALCANTI', 'PREFEITURA — CENTRO': 'PREFEITURA - ALFONSO CAVALCANTI',
    'IGREJA BATISTA DE COLÉGIO': 'IGREJA BATISTA DE COLÉGIO - COLÉGIO',
    'IGREJA BATISTA DO MANDELA - BENFICA': 'IGREJA BATISTA DO MANDELA - BENIFICA',
    'IGREJA BATISTA DO MANDELA — BENFICA': 'IGREJA BATISTA DO MANDELA - BENIFICA',
    'ASSEMBLEIA DE DEUS ADTS MANDELA - BENFICA': 'IGREJA BATISTA DO MANDELA - BENIFICA',
    'ASSEMBLEIA DE DEUS ADTS MANDELA — BENFICA': 'IGREJA BATISTA DO MANDELA - BENIFICA',
}

RESP_COLORS = {
    "CHARBEL": {"red": 0.678, "green": 0.847, "blue": 0.902},
    "CRISTIANE": {"red": 0.714, "green": 0.902, "blue": 0.714},
    "ENCCEJA": {"red": 1.000, "green": 0.949, "blue": 0.667},
    "OUTRO": {"red": 1.000, "green": 0.800, "blue": 0.800},
}
RESP_COLORS_ALT = {
    "CHARBEL": {"red": 0.565, "green": 0.753, "blue": 0.820},
    "CRISTIANE": {"red": 0.596, "green": 0.800, "blue": 0.596},
    "ENCCEJA": {"red": 0.961, "green": 0.878, "blue": 0.502},
    "OUTRO": {"red": 0.961, "green": 0.678, "blue": 0.678},
}
COR_MES_HEADER = {"red": 0.3, "green": 0.3, "blue": 0.3}
COR_MES_ATUAL = {"red": 0.2, "green": 0.5, "blue": 0.2}
COR_SEM_TURMA = {"red": 0.800, "green": 0.400, "blue": 0.400}


def normalize_local(local_name: str) -> str:
    upper = local_name.strip().upper()
    return NORMALIZACAO.get(upper, upper)


def get_chave_aba(row: list) -> str:
    raw_local = row[COL_LOCAL].strip() if len(row) > COL_LOCAL else ''
    curso = row[COL_CURSO].strip() if len(row) > COL_CURSO else ''
    canonical = normalize_local(raw_local)
    if canonical == LOCAL_MAANAIM:
        return LOCAL_MAANAIM_ENCCEJA if curso == CURSO_ENCCEJA else LOCAL_MAANAIM
    if canonical == LOCAL_INHOAIBA:
        return LOCAL_INHOAIBA_EBENEZER if curso in CURSOS_INHOAIBA_EBENEZER else LOCAL_INHOAIBA_ASSOC
    if canonical == LOCAL_COSMOS:
        return LOCAL_COSMOS_TENDA if curso in CURSOS_COSMOS_TENDA else LOCAL_COSMOS_ASSEMBLEIA
    return canonical


def get_responsavel(chave_aba: str) -> str:
    key = chave_aba.strip().upper()
    if key in [l.upper() for l in ENCCEJA_LOCAIS]:
        return "ENCCEJA"
    if key in [l.upper() for l in CRISTIANE_LOCAIS]:
        return "CRISTIANE"
    if key in [l.upper() for l in CHARBEL_LOCAIS]:
        return "CHARBEL"
    return "OUTRO"


# =============================================================================
# Autenticação Google Sheets
# Em produção (Render), configure a variável de ambiente GOOGLE_CREDENTIALS_JSON
# com o CONTEÚDO INTEIRO do arquivo JSON da service account (em uma linha só).
# =============================================================================

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
    client = gspread.authorize(creds)
    return client


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
    for char in ['\\', '/', '*', '?', ':', '[', ']']:
        name = name.replace(char, '_')
    return name.strip()


def parse_date(date_str: str):
    if not date_str or not date_str.strip():
        return None
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            pass
    return None


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


def cleanup_sheets(spreadsheet):
    keep = {ORIGIN_SHEET_NAME.upper(), "DADOS"}
    to_delete = [ws for ws in spreadsheet.worksheets() if ws.title.strip().upper() not in keep]
    for ws in to_delete:
        try:
            spreadsheet.del_worksheet(ws)
            time.sleep(1.5)
        except Exception:
            pass


def get_or_create_sheet(spreadsheet, title: str):
    sanitized = sanitize_sheet_name(title)
    for ws in spreadsheet.worksheets():
        if ws.title.strip().upper() == sanitized.strip().upper():
            spreadsheet.del_worksheet(ws)
            time.sleep(1.5)
            break
    sheet = retry_api_call(lambda: spreadsheet.add_worksheet(title=sanitized, rows=1000, cols=11))
    retry_api_call(lambda: sheet.update('A1:K1', [HEADERS]))
    return sheet


# Coluna A da aba DASHBOARD é reservada/preservada (uso manual do usuário).
# Todo o conteúdo gerado pelo sistema começa na coluna B.
COL_OFFSET = 1  # 1 coluna reservada (A) antes dos dados


def _get_or_create_dashboard_sheet(spreadsheet, min_cols: int, min_rows: int = 2000):
    try:
        sheet = spreadsheet.worksheet("DASHBOARD")
        # Garante espaço suficiente sem apagar a aba
        if sheet.col_count < min_cols:
            retry_api_call(lambda: sheet.resize(cols=min_cols))
        if sheet.row_count < min_rows:
            retry_api_call(lambda: sheet.resize(rows=min_rows))
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        return retry_api_call(lambda: spreadsheet.add_worksheet(title="DASHBOARD", rows=min_rows, cols=min_cols))


def _create_dashboard(spreadsheet, locals_dict: dict):
    EXCLUIR_DASHBOARD = {'CAMPO GRANDE'}
    today = agora_brasilia().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=6)
    month_start = today.replace(day=1)

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
    mes_atual_ym = (today.year, today.month)
    mes_atual_idx = meses.index(mes_atual_ym) if mes_atual_ym in meses else -1

    contagem_mensal = {}
    for chave_aba, registros in locals_dict.items():
        contagem_mensal[chave_aba] = defaultdict(int)
        for row in registros:
            d = parse_date(row[COL_DATA])
            if d:
                contagem_mensal[chave_aba][(d.year, d.month)] += 1

    # 8 colunas fixas (sem ÚLTIMA DATA)
    COLS_FIXAS = 8
    total_cols = COLS_FIXAS + n_meses          # colunas de conteúdo (a partir da coluna B)
    total_cols_sheet = total_cols + COL_OFFSET  # total incluindo a coluna A reservada

    sheet = _get_or_create_dashboard_sheet(spreadsheet, min_cols=total_cols_sheet + 2)

    # Limpa somente as colunas B em diante (preserva a coluna A), valores e formatação
    ultima_col_letra = rowcol_to_a1(1, total_cols_sheet + 5).rstrip('1')
    retry_api_call(lambda: sheet.batch_clear([f"B1:{ultima_col_letra}5000"]))
    time.sleep(1)
    retry_api_call(lambda: spreadsheet.batch_update({"requests": [
        {
            "repeatCell": {
                "range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 5000,
                           "startColumnIndex": 1, "endColumnIndex": total_cols_sheet + 5},
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat"
            }
        },
        {
            "setDataValidation": {
                "range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 5000,
                           "startColumnIndex": 1, "endColumnIndex": total_cols_sheet + 5}
            }
        },
    ]}))

    headers = (
        ['RESPONSÁVEL', 'LOCAL', 'TOTAL', 'MÊS ATUAL', 'ONTEM', 'SEMANA',
         'DATA DE INÍCIO', 'STATUS']
        + [mes_label(y, m) for y, m in meses]
    )

    end_col = rowcol_to_a1(1, total_cols_sheet).split('1')[0]
    retry_api_call(lambda: sheet.update(f"B1:{end_col}1", [headers]))

    dashboard_data = []
    processed = set()

    def build_row(chave_aba, registros):
        y_count = w_count = m_count = 0
        datas = []
        for row in registros:
            d = parse_date(row[COL_DATA])
            if d:
                datas.append(d.date())
                if d.date() == yesterday:
                    y_count += 1
                if week_ago <= d.date() <= today:
                    w_count += 1
                if month_start <= d.date() <= today:
                    m_count += 1
        responsavel = get_responsavel(chave_aba)
        primeira = DATAS_INICIO_FIXAS.get(chave_aba, min(datas).strftime('%d/%m/%Y') if datas else '')
        status = 'SEM TURMA' if chave_aba in SEM_TURMA else 'COM TURMA'
        fixos = [responsavel, chave_aba, len(registros), m_count, y_count, w_count, primeira, status]
        mensais = [contagem_mensal.get(chave_aba, {}).get(ym, 0) for ym in meses]
        return fixos + mensais

    for chave_aba, registros in locals_dict.items():
        if chave_aba.strip().upper() in {x.upper() for x in EXCLUIR_DASHBOARD}:
            continue
        dashboard_data.append(build_row(chave_aba, registros))
        processed.add(chave_aba.strip().upper())

    for locais_list in [CHARBEL_LOCAIS, CRISTIANE_LOCAIS, ENCCEJA_LOCAIS]:
        seen = set()
        for local_name in locais_list:
            key = local_name.strip().upper()
            if key in {x.upper() for x in EXCLUIR_DASHBOARD}:
                continue
            if key not in processed and key not in seen:
                responsavel = get_responsavel(local_name)
                primeira = DATAS_INICIO_FIXAS.get(local_name, '')
                status = 'SEM TURMA' if local_name in SEM_TURMA else 'COM TURMA'
                fixos = [responsavel, local_name, 0, 0, 0, 0, primeira, status]
                mensais = [0] * n_meses
                dashboard_data.append(fixos + mensais)
                seen.add(key)
                processed.add(key)

    dashboard_data.sort(key=lambda x: (x[0], x[1].upper()))

    if dashboard_data:
        end_data = rowcol_to_a1(len(dashboard_data) + 1, total_cols_sheet).split(str(len(dashboard_data) + 1))[0]
        retry_api_call(lambda: sheet.update(f"B2:{end_data}{len(dashboard_data)+1}", dashboard_data))

    total_row = len(dashboard_data) + 2

    def col_letter(idx):
        return rowcol_to_a1(1, idx).rstrip('1')

    # Índices de coluna (1-based) considerando o deslocamento pela coluna A
    c_total = col_letter(COL_OFFSET + 3)
    c_mes_atual = col_letter(COL_OFFSET + 4)
    c_ontem = col_letter(COL_OFFSET + 5)
    c_semana = col_letter(COL_OFFSET + 6)
    c_local = col_letter(COL_OFFSET + 2)

    # Totais calculados em Python (não são fórmulas do Sheets — já vêm prontos)
    soma_total = sum(row[2] for row in dashboard_data)
    soma_mes_atual = sum(row[3] for row in dashboard_data)
    soma_ontem = sum(row[4] for row in dashboard_data)
    soma_semana = sum(row[5] for row in dashboard_data)
    somas_meses = [sum(row[8 + i] for row in dashboard_data) for i in range(n_meses)]

    total_locais = len(dashboard_data)
    linha_total = ['TOTAL', total_locais, soma_total, soma_mes_atual, soma_ontem, soma_semana, '', ''] + somas_meses
    end_tot = rowcol_to_a1(total_row, total_cols_sheet).split(str(total_row))[0]
    retry_api_call(lambda: sheet.update(f"B{total_row}:{end_tot}{total_row}", [linha_total]))


    time.sleep(2)
    O = COL_OFFSET
    fmt = [
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 0, "endRowIndex": 1,
            "startColumnIndex": O, "endColumnIndex": O + COLS_FIXAS},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0},
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
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sheet.id,
            "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 3}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
        # Coluna LOCAL bem mais larga, com quebra de linha para caber o nome inteiro
        {"updateDimensionProperties": {"range": {"sheetId": sheet.id, "dimension": "COLUMNS",
            "startIndex": O + 1, "endIndex": O + 2}, "properties": {"pixelSize": 420}, "fields": "pixelSize"}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": 1, "endRowIndex": total_row,
            "startColumnIndex": O + 1, "endColumnIndex": O + 2},
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

    for i, row_data in enumerate(dashboard_data):
        row_index = i + 1
        responsavel = row_data[0]
        bg = RESP_COLORS.get(responsavel, {"red": 1.0, "green": 1.0, "blue": 1.0})
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": row_index, "endRowIndex": row_index + 1,
            "startColumnIndex": O, "endColumnIndex": O + COLS_FIXAS - 1}, "cell": {"userEnteredFormat": {"backgroundColor": bg}},
            "fields": "userEnteredFormat(backgroundColor)"}})
        status_val = row_data[7]
        status_bg = COR_SEM_TURMA if status_val == 'SEM TURMA' else {"red": 0.55, "green": 0.78, "blue": 0.55}
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": row_index, "endRowIndex": row_index + 1,
            "startColumnIndex": O + COLS_FIXAS - 1, "endColumnIndex": O + COLS_FIXAS},
            "cell": {"userEnteredFormat": {"backgroundColor": status_bg,
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
        fmt.append({"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": row_index, "endRowIndex": row_index + 1,
            "startColumnIndex": O + COLS_FIXAS, "endColumnIndex": O + total_cols},
            "cell": {"userEnteredFormat": {"backgroundColor": bg}},
            "fields": "userEnteredFormat(backgroundColor)"}})

    retry_api_call(lambda: spreadsheet.batch_update({"requests": fmt}))

    # Reforço final: limpa qualquer validação de dados/chip residual na linha de total
    # e reaplica preto/branco por cima de tudo, garantindo o mesmo visual do cabeçalho
    retry_api_call(lambda: spreadsheet.batch_update({"requests": [
        {"setDataValidation": {"range": {"sheetId": sheet.id, "startRowIndex": total_row - 1, "endRowIndex": total_row,
            "startColumnIndex": O, "endColumnIndex": O + total_cols}}},
        {"repeatCell": {"range": {"sheetId": sheet.id, "startRowIndex": total_row - 1, "endRowIndex": total_row,
            "startColumnIndex": O, "endColumnIndex": O + total_cols},
            "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0},
                "textFormat": {"foregroundColor": {"red": 0.0, "green": 0.898, "blue": 1.0}, "bold": True, "fontSize": 10, "fontFamily": "Arial"},
                "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
    ]}))
    return len(dashboard_data), n_meses


def atualizar_dashboard():
    """Recria a aba DASHBOARD a partir da aba DADOS. Retorna resumo (dict)."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    origin = spreadsheet.worksheet(ORIGIN_SHEET_NAME)

    cleanup_sheets(spreadsheet)

    data = origin.get_all_values()
    rows = data[1:]

    locals_dict = {}
    for row in rows:
        if len(row) > COL_LOCAL:
            chave = get_chave_aba(row)
            if chave:
                locals_dict.setdefault(chave, []).append(row)

    for chave, registros in locals_dict.items():
        sheet = get_or_create_sheet(spreadsheet, chave)
        new_rows = []
        for r in registros:
            r = list(r)
            while len(r) < 11:
                r.append('')
            new_rows.append(r[:11])
        if new_rows:
            retry_api_call(lambda rows=new_rows, s=sheet: s.update(f"A2:K{len(rows)+1}", rows))
            time.sleep(1.5)

    n_locais, n_meses = _create_dashboard(spreadsheet, locals_dict)
    return {
        "ok": True,
        "locais": n_locais,
        "meses": n_meses,
        "atualizado_em": agora_brasilia().strftime('%d/%m/%Y %H:%M:%S'),
    }


def ler_dashboard_atual():
    """Lê a aba DASHBOARD tal como está agora (sem recriar) — usado para o PDF.
    A coluna A é reservada para uso manual e não entra no relatório."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.worksheet("DASHBOARD")
    values = sheet.get_all_values()
    if not values:
        return {"headers": [], "rows": []}
    headers = values[0][COL_OFFSET:]
    corpo = [r[COL_OFFSET:] for r in values[1:]]

    # Encontra a última linha com dados na coluna LOCAL (índice 1 após remover a coluna A)
    ultima_com_dado = -1
    for i, r in enumerate(corpo):
        if len(r) > 1 and r[1].strip():
            ultima_com_dado = i

    if ultima_com_dado == -1:
        return {"headers": headers, "rows": []}

    # Inclui todas as linhas de dados + a linha seguinte (linha de total, em preto/sem texto)
    limite = min(ultima_com_dado + 2, len(corpo))
    rows = corpo[:limite]
    return {"headers": headers, "rows": rows}


def obter_dashboard_visual():
    """Monta os KPIs e dados de gráficos (estilo QualificaTech) a partir da aba DADOS."""
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return analisar_dados_visual(spreadsheet, COL_DATA, COL_GENERO, COL_CURSO, COL_LOCAL,
                                  origin_sheet_name=ORIGIN_SHEET_NAME)


def ler_dashboard_filtrado_por_responsavel(responsavel: str):
    """Lê a aba DASHBOARD e devolve só as linhas de um responsável (ex: ENCCEJA),
    recalculando a linha de total apenas com os locais filtrados."""
    dados = ler_dashboard_atual()
    headers = dados["headers"]
    linhas = dados["rows"]

    linhas_dados = [r for r in linhas if r and str(r[0]).strip().upper() != "TOTAL"]
    alvo = responsavel.strip().upper()
    filtradas = [r for r in linhas_dados if len(r) > 0 and str(r[0]).strip().upper() == alvo]

    def to_int(v):
        try:
            return int(str(v).strip())
        except Exception:
            return 0

    n_fixas = 8  # RESPONSÁVEL, LOCAL, TOTAL, MÊS ATUAL, ONTEM, SEMANA, DATA DE INÍCIO, STATUS
    n_cols = len(headers)
    somas_meses = [0] * max(n_cols - n_fixas, 0)
    soma_total = soma_mes = soma_ontem = soma_semana = 0

    for r in filtradas:
        soma_total += to_int(r[2]) if len(r) > 2 else 0
        soma_mes += to_int(r[3]) if len(r) > 3 else 0
        soma_ontem += to_int(r[4]) if len(r) > 4 else 0
        soma_semana += to_int(r[5]) if len(r) > 5 else 0
        for i in range(n_fixas, n_cols):
            if len(r) > i:
                somas_meses[i - n_fixas] += to_int(r[i])

    linha_total = ["TOTAL", len(filtradas), soma_total, soma_mes, soma_ontem, soma_semana, "", ""] + somas_meses
    return {"headers": headers, "rows": filtradas + [linha_total]}
