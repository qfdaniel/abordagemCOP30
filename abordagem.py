# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import base64
import unicodedata
from pathlib import Path
from typing import Optional, Dict, List

# ================= AJUSTES RÁPIDOS (estilo) =================
# Altura aumentada +10% (4.65 * 1.10 = 5.12) e espaçamento reduzido
BTN_HEIGHT = "5.12em"  # Altura de TODOS os botões
BTN_GAP    = "3px"     # Espaçamento vertical unificado
# ============================================================

# --- CONFIG DA PÁGINA ---
st.set_page_config(
    page_title="App COP30",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTES ---
TITULO_PRINCIPAL = "App COP30"
OBRIG = ":red[**\\***]"  # asterisco obrigatório
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1b2GOAOIN6mvgLH1rpvRD1vF4Ro9VOqylKkXaUTAq0Ro/edit"

# Link do botão "Mapa das Estações" (atualizado)
MAPS_URL = "https://www.google.com/maps/d/u/0/edit?mid=1E7uIgoEchrY_KQn4jzu4ePs8WrdWwxc&usp=sharing"

# Mapeamento RFeye -> Região (para dropdown do 1º botão)
MAPEAMENTO_CODIGO = {
    "RFeye002093": "Anatel",
    "RFeye002303": "Parque da Cidade",
    "RFeye002315": "Docas",
    "RFeye002012": "Terminal de Outeiro",
    "RFeye002175": "Aldeia",
    "RFeye002129": "Mangueirinho",
}

# Mapeamento RFeye -> Nome completo da aba
MAPEAMENTO_ABAS = {
    "RFeye002093": "RFeye002093 - ANATEL",
    "RFeye002303": "RFeye002303 - PARQUE DA CIDADE",
    "RFeye002315": "RFeye002315 - DOCAS",
    "RFeye002012": "RFeye002012 - OUTEIRO",
    "RFeye002175": "RFeye002175 - ALDEIA",
    "RFeye002129": "RFeye002129 - MANGUEIRINHO",
}
TODAS_ABAS_RFEYE = list(MAPEAMENTO_ABAS.values())

# Opções fixas de Identificação (edição do 1º botão)
IDENT_OPCOES = [
    "Sinal de dados",
    "Comunicação (voz) relacionada ao evento",
    "Comunicação (voz) não relacionada ao evento",
    "Sinal não relacionado ao evento",
    "Espúrio ou Produto de Intermodulação",
    "Ruído",
    "Não identificado",
]

# Opções Faixa de Frequência (OBRIGATÓRIA)
FAIXA_OPCOES = [
    "FM", "SMA", "SMM", "SLP", "TV", "SMP", "GNSS", "Satélite", "Radiação Restrita",
]

# --- LOGOS (BASE64) ---
def _img_b64(path: str) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")

def render_header(esquerda: str = "logo.png", direita: str = "anatel.png"):
    left_b64  = _img_b64(esquerda)
    right_b64 = _img_b64(direita)
    left_tag  = f'<img class="hdr-img hdr-left" src="data:image/png;base64,{left_b64}" alt="Logo esquerda">' if left_b64 else ""
    right_tag = f'<img class="hdr-img hdr-right" src="data:image/png;base64,{right_b64}" alt="Logo direita">' if right_b64 else ""
    st.markdown(
        f"""
        <div class="header-logos">
            {left_tag}
            <h2>{TITULO_PRINCIPAL}</h2>
            {right_tag}
        </div>
        """,
        unsafe_allow_html=True
    )

# --- CSS — implementando as SUGESTÕES do usuário ---
st.markdown(f"""
<style>
  /* ===== CONFIG GERAL ===== */
  :root{{
    --btn-height: {BTN_HEIGHT};   /* <<< ALTURA FIXA (aumentada) */
    --btn-gap: {BTN_GAP};         /* <<< ESPAÇAMENTO VERTICAL (ajustado) */
    --btn-font: 1.02em;
  }}

  .block-container {{ max-width: 760px; padding-top: .45rem; padding-bottom: .55rem; margin: 0 auto; }}
  .stApp {{ background-color: #D7D6D4; }}
  #MainMenu, footer, header {{ visibility: hidden; }}
...
  #MainMenu, footer, header {{ visibility: hidden; }}

  /* =========================================
     CORREÇÃO DO GAP HORIZONTAL DAS COLUNAS
     ========================================= */
  div[data-testid="stHorizontalBlock"] {{
    gap: 0rem !important;
  }}

  /* Labels pretos + leve sombra */
  div[data-testid="stWidgetLabel"] > label {{ color:#000 !important; text-shadow: 0 1px 0 rgba(0,0,0,.05); }}
...
  /* Labels pretos + leve sombra */
  div[data-testid="stWidgetLabel"] > label {{ color:#000 !important; text-shadow: 0 1px 0 rgba(0,0,0,.05); }}
  legend {{ color:#000 !important; text-shadow: 0 1px 0 rgba(0,0,0,.05); }}

  /* Remove span do header */
  span[data-testid="stHeaderActionElements"] {{ display: none !important; }}

  /* AJUSTE NA LINHA E ESPAÇAMENTO - INÍCIO */
  .header-logos + div[data-testid="stElementContainer"] hr {{
    margin-top: 0 !important;
    margin-bottom: .06rem !important;      /* Espaço entre linha e 1º botão (reduzido) */
    height: 2px !important;                /* Linha um pouco mais grossa */
    background-color: #888 !important;     /* Cor da linha */
    border: none !important;               /* Remove a borda padrão */
  }}
  /* AJUSTE NA LINHA E ESPAÇAMENTO - FIM */

  /* Reduz hr em geral */
  div[data-testid="stMarkdownContainer"] hr {{
    margin-top: .35rem !important;
    margin-bottom: .35rem !important;
  }}

  /* ===== Header (título + logos) ===== */
  .header-logos {{
    display: grid; grid-template-columns: 1fr auto 1fr;
    align-items: center; gap: 12px; text-align: center; margin-bottom: .05rem;
  }}
  .hdr-img {{ height:56px; }}
  .hdr-left {{ justify-self: end; }}
  .hdr-right {{ justify-self: start; }}
  .header-logos h2{{
    margin:0; color:#1A311F; font-weight:800;
    text-shadow: 1px 1px 0 rgba(255,255,255,.35), 0 1px 2px rgba(0,0,0,.28);
    font-size:2rem; line-height:1.1; grid-column:2;
  }}

  /* =========================================
     BOTÕES DO APP (padrão + menu + links)
     ========================================= */

  /* Padrão para TODOS os botões */
  .stButton > button, .app-btn, div[data-testid="stLinkButton"] a {{
    width:100%;
    height: var(--btn-height);
    min-height: var(--btn-height);
    font-size: var(--btn-font) !important;
    font-weight:600 !important;
    padding:0 12px !important;
    line-height:1.15 !important;
    border-radius:8px !important;
    border: 3.4px solid #54515c !important;
    color: white !important;
    text-shadow: 0 1px 0 rgba(0,0,0,.45), 0 0 2px rgba(0,0,0,.25) !important;
    box-shadow: 2px 2px 5px rgba(0,0,0,.3) !important;
    transition: all .2s ease-in-out !important;
    text-align: center;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 0 var(--btn-gap) 0 !important;
    white-space: normal !important;
    overflow: hidden !important;
    text-decoration: none !important;
  }}

  /* Efeito Hover para TODOS os botões */
  .stButton > button:hover, .app-btn:hover, div[data-testid="stLinkButton"] a:hover {{
    filter: brightness(1.03) !important;
    border-color: white !important;
    box-shadow: 4px 4px 8px rgba(0,0,0,.4) !important;
    transform: translateY(-2px) !important;
  }}

  /* Fundo AZUL padrão */
  .stButton > button, .app-btn, div[data-testid="stLinkButton"] a {{
     background: linear-gradient(to bottom, #14337b, #4464A7) !important;
  }}

  /* --- ESTILO DOS BOTÕES VERMELHOS (CORREÇÃO FINAL) --- */
  #marker-vermelho {{ display: none; }} /* Oculta a âncora */
  
  /* Remove o espaço do container da âncora */
  div[data-testid="stElementContainer"]:has(#marker-vermelho) {{
      margin-bottom: 0 !important;
  }}

  /* Seleciona o container da âncora, e a partir dele, os 3 containers de botão seguintes */
  div[data-testid="stElementContainer"]:has(#marker-vermelho) ~ div[data-testid="stElementContainer"]:nth-of-type(-n+4) .stButton > button {{
    background: linear-gradient(to bottom, #c62828, #e53935) !important;
    border-color: #a92222 !important;
    text-shadow: 0 1px 1px rgba(0,0,0,.4) !important;
  }}
  
  .confirm-warning{{ background:linear-gradient(to bottom, #d9534f, #c9302c); color:white; font-weight:800; text-align:center; padding:1rem; border-radius:8px; margin-bottom:1rem; }}
  .info-green {{ background: linear-gradient(to bottom, #1b5e20, #2e7d32); color: #fff; font-weight: 700; text-align: center; padding: .8rem 1rem; border-radius: 8px; margin: .25rem 0 1rem; }}

  /* =========================================
     MOBILE — Galaxy S24 (~393px)
     ========================================= */
  @media (max-width: 420px){{
    :root{{
      --btn-height: 3.5em; /* Altura AUMENTADA para mobile */
      --btn-gap: 4px;      /* Espaçamento REDUZIDO para mobile */
      --btn-font: 0.98em;
    }}
    .hdr-img{{ height:38px; }}
    .header-logos h2{{ font-size:1.42rem; }}
    .block-container{{ padding:.4rem .6rem; }}
    div[data-testid="stDivider"]{{ margin: .25rem 0 .25rem 0 !important; }}

    .ute-table th, .ute-table td {{
        padding: 4px;
        font-size: 0.85em;
        word-break: break-word;
    }}
  }}

  /* Tradutor de Voz (último botão) VERDE CLARO */
  div[data-testid="stLinkButton"] a[href*="translate.google.com"] {{
    background: linear-gradient(to bottom, #2e7d32, #4caf50) !important;
    border-color: #1b5e20 !important;
  }}
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO GSPREAD ---
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    scoped = creds.with_scopes([
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    return gspread.authorize(scoped)

# ===================== HELPERS =====================
def _first_col_match(columns, *preds):
    for c in columns:
        s = (c or "").strip().lower()
        for p in preds:
            if p(s): return c
    return None

def _extract_rfeye_code(estacao_str: str) -> str:
    if not estacao_str: return ""
    m = re.search(r"(RFeye\d{6})", estacao_str, flags=re.IGNORECASE)
    return m.group(1) if m else ""

def _map_local_by_estacao(estacao_str: str) -> str:
    code = _extract_rfeye_code(estacao_str)
    return MAPEAMENTO_CODIGO.get(code, estacao_str) if code else estacao_str

def _normalize_aba_name(estacao_raw: str) -> str:
    if not estacao_raw:
        return estacao_raw
    code = _extract_rfeye_code(estacao_raw)
    if code and code in MAPEAMENTO_ABAS:
        return MAPEAMENTO_ABAS[code]
    return estacao_raw

def _parse_data_ddmmyyyy(s):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    return date.today()

def _col_to_index(letter: str) -> int:
    letter = (letter or "").upper()
    res = 0
    for ch in letter:
        if not ('A' <= ch <= 'Z'): continue
        res = res * 26 + (ord(ch) - ord('A') + 1)
    return res

def _first_empty_row_in_block(aba, start_col_letter: str, end_col_letter: str) -> int:
    start_idx = _col_to_index(start_col_letter)
    end_idx   = _col_to_index(end_col_letter)

    max_len = 1
    for idx in range(start_idx, end_idx + 1):
        try:
            vals = aba.col_values(idx)
            if len(vals) > max_len:
                max_len = len(vals)
        except Exception:
            pass
    if max_len < 1:
        max_len = 1

    rng = f"{start_col_letter}1:{end_col_letter}{max_len}"
    try:
        rows = aba.get(rng)
    except Exception:
        rows = []

    if len(rows) < max_len:
        rows += [[""] * (end_idx - start_idx + 1) for _ in range(max_len - len(rows))]

    for i, row in enumerate(rows, start=1):
        if all((c or "").strip() == "" for c in row):
            return i
    return max_len + 1

def _first_row_where_col_empty(aba, col_letter: str, start_row: int = 2) -> int:
    col_idx = _col_to_index(col_letter)
    try:
        col_vals = aba.col_values(col_idx)
    except Exception:
        col_vals = []

    if len(col_vals) < start_row:
        return start_row

    for i in range(start_row-1, len(col_vals)):
        if (col_vals[i] or "").strip() == "":
            return i + 1

    return len(col_vals) + 1

def _next_sequential_id(aba, col_letter: str = "H", start_row: int = 2) -> int:
    col_idx = _col_to_index(col_letter)
    try:
        col_vals = aba.col_values(col_idx)
    except Exception:
        col_vals = []

    max_id = 0
    for i, v in enumerate(col_vals, start=1):
        if i < start_row:
            continue
        s = (v or "").strip()
        if not s:
            continue
        try:
            n = int(s)
            if n > max_id:
                max_id = n
        except:
            pass
    return max_id + 1 if max_id >= 0 else 1

def _valid_neg_coord(value: str) -> bool:
    if value is None:
        return True
    v = value.strip()
    if v == "":
        return True
    return re.match(r"^-\d+\.\d{6}$", v) is not None

# ---------- Normalização para busca ----------
def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.strip().lower()

def _contains_norm(series: pd.Series, termo: str) -> pd.Series:
    termo_norm = _normalize_text(termo)
    return series.fillna("").astype(str).apply(lambda x: termo_norm in _normalize_text(x))

def _as_bool_sim(valor: str) -> bool:
    s = (str(valor or "")).strip().lower()
    return s in ("sim", "true", "1", "x", "ok")

# --------- DEDUPLICAÇÃO DE NOMES DE COLUNAS ---------
def _dedupe_columns_index(columns):
    counts = {}
    new_cols = []
    for c in columns:
        name = (str(c) if c is not None else "").strip() or "col"
        if name in counts:
            counts[name] += 1
            new_cols.append(f"{name}.{counts[name]}")
        else:
            counts[name] = 0
            new_cols.append(name)
    return new_cols

# --------- STRING SEGURA ---------
def _safe_str(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    s_low = s.lower()
    if s_low in ("nan", "none", "na", "n/a", "null", "-", "--", "—"):
        return ""
    return s

# ========== LEITURA DE DADOS DAS ABAS ==========
@st.cache_data(ttl=180)
def carregar_dados_ute(_client):
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet("Tabela UTE")
        
        matriz = aba.get_all_values()
        if not matriz or len(matriz) < 2:
            return pd.DataFrame()

        # Colunas: A (País), E (Frequência), F (Largura), H (Processo)
        # Índices baseados em 0: 0, 4, 5, 7
        dados = []
        for row in matriz[1:]: # Pula o cabeçalho
            if len(row) > 7: # Garante que a linha tem dados suficientes
                 dados.append({
                    "País": row[0],
                    "Frequência (MHz)": row[4],
                    "Largura (kHz)": row[5],
                    "Processo SEI": row[7]
                })

        df = pd.DataFrame(dados)
        df = df[df["Processo SEI"].str.strip() != ""] # Filtra linhas sem Processo SEI
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error("Aba 'Tabela UTE' não encontrada na planilha.")
        return pd.DataFrame()
    except Exception as e:
        st.error("Erro ao carregar dados da Tabela UTE.")
        st.exception(e)
        return pd.DataFrame()

@st.cache_data(ttl=180)
def carregar_pendencias_painel_mapeadas(_client):
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet("PAINEL")

        matriz = aba.get("A1:AF")
        if not matriz or len(matriz) < 2:
            return pd.DataFrame()

        header, rows = matriz[0], matriz[1:]
        df = pd.DataFrame(rows, columns=header)

        def col_like(*checks):
            return _first_col_match(df.columns, *[(lambda s, c=c: c(s)) for c in checks])

        col_situ = col_like(lambda s: s == "situação", lambda s: s == "situacao")
        col_est  = col_like(lambda s: "estação" in s, lambda s: "estacao" in s)
        col_id   = col_like(lambda s: s == "id")

        col_fiscal   = col_like(lambda s: "fiscal" in s)
        col_data     = col_like(lambda s: s == "data" or s == "dia")
        col_hora     = col_like(lambda s: "hh" in s or "hora" in s or "h:" in s)
        col_freq     = col_like(lambda s: "frequência" in s or "frequencia" in s)
        col_bw       = col_like(lambda s: "largura" in s)
        col_faixa    = col_like(lambda s: "faixa" in s and "envolvida" in s)
        col_ident    = col_like(lambda s: "identificação" in s or "identificacao" in s)
        col_autz     = col_like(lambda s: "autorizado" in s)
        col_ute      = col_like(lambda s: s.strip() == "ute" or "ute?" in s)
        col_processo = col_like(lambda s: "processo" in s and "sei" in s)
        col_obs      = col_like(lambda s: "ocorrência" in s or "ocorrencia" in s or "observa" in s)
        col_ciente   = col_like(lambda s: "ciente" in s)
        col_interf   = col_like(lambda s: "interferente" in s)

        if not (col_situ and col_est and col_id):
            return pd.DataFrame()

        situ = df[col_situ].astype(str).str.strip().str.lower()
        pend = df[situ.eq("pendente")].copy()
        if pend.empty:
            return pd.DataFrame()

        out = pd.DataFrame()
        out["Local"] = pend[col_est].map(_map_local_by_estacao)
        out["EstacaoRaw"] = pend[col_est]
        out["ID"]                = pend[col_id]
        out["Fiscal"]            = pend[col_fiscal] if col_fiscal else ""
        out["Data"]              = pend[col_data] if col_data else ""
        out["HH:mm"]             = pend[col_hora] if col_hora else ""
        out["Frequência (MHz)"]  = pend[col_freq] if col_freq else ""
        out["Largura (kHz)"]     = pend[col_bw] if col_bw else ""
        out["Faixa de Frequência Envolvida"] = pend[col_faixa] if col_faixa else ""
        out["Identificação"]                 = pend[col_ident] if col_ident else ""
        out["Autorizado?"]                   = pend[col_autz]  if col_autz else ""
        out["UTE?"]                          = pend[col_ute]   if col_ute else ""
        out["Processo SEI UTE"]              = pend[col_processo] if col_processo else ""
        out["Ocorrência (observações)"]      = pend[col_obs]   if col_obs else ""
        out["Alguém mais ciente?"]           = pend[col_ciente] if col_ciente else ""
        out["Interferente?"]                 = pend[col_interf] if col_interf else ""
        out["Situação"]                      = pend[col_situ]

        out = out.sort_values(by=["Local", "Data"], kind="stable", na_position="last").reset_index(drop=True)
        out["Fonte"] = "PAINEL"
        return out

    except Exception as e:
        st.error("Erro ao carregar pendências da aba 'PAINEL'.")
        st.exception(e)
        return pd.DataFrame()

@st.cache_data(ttl=180)
def carregar_pendencias_abordagem_pendentes(_client):
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet("Abordagem")
        matriz = aba.get("H1:W")
        if not matriz or len(matriz) < 2:
            return pd.DataFrame()

        header, rows = matriz[0], matriz[1:]
        df = pd.DataFrame(rows, columns=header)

        def col_or_pos(name, pos_letter):
            if name in df.columns:
                return df[name]
            pos_map = {"H":0,"I":1,"J":2,"K":3,"L":4,"M":5,"N":6,"O":7,"P":8,"Q":9,"R":10,"S":11,"T":12,"U":13,"V":14,"W":15}
            idx = pos_map[pos_letter]
            return pd.Series([r[idx] if len(r)>idx else "" for r in rows])

        colH = col_or_pos("H", "H")  # ID
        colI = col_or_pos("I", "I")  # Local/Região
        colJ = col_or_pos("J", "J")  # Fiscal
        colK = col_or_pos("K", "K")  # Data
        colM = col_or_pos("M", "M")  # Frequência
        colN = col_or_pos("N", "N")  # Largura
        colO = col_or_pos("O", "O")  # Faixa de Frequência
        colT = col_or_pos("T", "T")  # Observações
        colV = col_or_pos("V", "V")  # Interferente?
        colW = col_or_pos("W", "W")  # Situação

        pend = pd.DataFrame({
            "Local": colI.fillna("").astype(str),
            "EstacaoRaw": pd.Series(["ABORDAGEM"]*len(colI)),
            "ID": colH.fillna("").astype(str),
            "Fiscal": colJ.fillna("").astype(str),
            "Data": colK.fillna("").astype(str),
            "HH:mm": pd.Series([""]*len(colI)),
            "Frequência (MHz)": colM.fillna("").astype(str),
            "Largura (kHz)": colN.fillna("").astype(str),
            "Faixa de Frequência Envolvida": colO.fillna("").astype(str),
            "Identificação": pd.Series([""]*len(colI)),
            "Autorizado?": pd.Series([""]*len(colI)),
            "UTE?": pd.Series([""]*len(colI)),
            "Processo SEI UTE": pd.Series([""]*len(colI)),
            "Ocorrência (observações)": colT.fillna("").astype(str),
            "Alguém mais ciente?": pd.Series([""]*len(colI)),
            "Interferente?": colV.fillna("").astype(str),
            "Situação": colW.fillna("").astype(str),
            "Fonte": pd.Series(["ABORDAGEM"]*len(colI)),
        })

        pend = pend[ pend["Situação"].str.strip().str.lower().eq("pendente") ].copy()
        pend = pend.sort_values(by=["Local","Data"], kind="stable", na_position="last").reset_index(drop=True)
        return pend

    except Exception as e:
        st.error("Erro ao carregar pendências da aba 'Abordagem'.")
        st.exception(e)
        return pd.DataFrame()

# ============== ATUALIZAÇÃO NAS ABAS-MÃE ==============
def _find_header_col_index(header_list: List[str], *preds) -> Optional[int]:
    for idx, name in enumerate(header_list, start=1):
        s = (name or "").strip().lower()
        for p in preds:
            if p(s): return idx
    return None

def atualizar_campos_na_aba_mae(_client, estacao_raw, id_ocorrencia, novos_valores: Dict[str, str]) -> str:
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba_nome = _normalize_aba_name(estacao_raw)
        aba = planilha.worksheet(aba_nome)
    except gspread.exceptions.WorksheetNotFound:
        return f"ERRO: Aba mãe '{_normalize_aba_name(estacao_raw) or estacao_raw}' não encontrada."
    except Exception as e:
        return f"ERRO ao abrir planilha: {e}"

    try:
        header = aba.row_values(1)
        cell = aba.find(str(id_ocorrencia), in_column=1)
        if not cell:
            return f"ERRO: ID {id_ocorrencia} não encontrado na aba '{aba.title}'."
        row_idx = cell.row

        def find_col(*checks):
            return _find_header_col_index(header, *[(lambda s, c=c: c(s)) for c in checks])

        c_situ  = find_col(lambda s: s == "situação", lambda s: s == "situacao") or 16
        c_iden  = find_col(lambda s: "identificação" in s or "identificacao" in s)
        c_autz  = find_col(lambda s: "autorizado" in s)
        c_ute   = find_col(lambda s: s.strip() == "ute" or "ute?" in s)
        c_proc  = find_col(lambda s: ("processo" in s and "sei" in s))
        c_obs   = find_col(lambda s: "ocorrência" in s or "ocorrencia" in s or "observa" in s)
        c_cient = find_col(lambda s: "ciente" in s)
        c_inter = find_col(lambda s: "interferente" in s)

        updates = []
        if "Situação" in novos_valores and c_situ: updates.append((row_idx, c_situ, novos_valores["Situação"]))
        if "Identificação" in novos_valores and c_iden: updates.append((row_idx, c_iden, novos_valores["Identificação"]))
        if "Autorizado?" in novos_valores and c_autz: updates.append((row_idx, c_autz, novos_valores["Autorizado?"]))
        if "UTE?" in novos_valores and c_ute: updates.append((row_idx, c_ute, novos_valores["UTE?"]))
        if "Processo SEI UTE" in novos_valores and c_proc: updates.append((row_idx, c_proc, novos_valores["Processo SEI UTE"]))
        if "Ocorrência (observações)" in novos_valores and c_obs: updates.append((row_idx, c_obs, novos_valores["Ocorrência (observações)"]))
        if "Alguém mais ciente?" in novos_valores and c_cient: updates.append((row_idx, c_cient, novos_valores["Alguém mais ciente?"]))
        if "Interferente?" in novos_valores and c_inter: updates.append((row_idx, c_inter, novos_valores["Interferente?"]))

        for r, c, v in updates:
            aba.update_cell(r, c, v)

        return f"Ocorrência {id_ocorrencia} atualizada na aba '{aba.title}'."
    except Exception as e:
        return f"ERRO ao atualizar a aba '{aba.title}': {e}"

# ============== ATUALIZAÇÃO NA ABORDAGEM POR ID (H) ==============
def atualizar_campos_abordagem_por_id(_client, id_h: str, novos_valores: Dict[str, str]) -> str:
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet("Abordagem")

        cell = aba.find(str(id_h), in_column=_col_to_index("H"))
        if not cell:
            return f"Registro (ID={id_h}) não encontrado na 'Abordagem'."
        row_idx = cell.row

        writes = []
        if "Identificação" in novos_valores:
            writes.append(("P", novos_valores["Identificação"]))
        if "Autorizado?" in novos_valores:
            writes.append(("Q", novos_valores["Autorizado?"]))
        if "UTE?" in novos_valores:
            writes.append(("R", novos_valores["UTE?"]))
        if "Processo SEI UTE" in novos_valores:
            writes.append(("S", novos_valores["Processo SEI UTE"]))
        if "Ocorrência (observações)" in novos_valores:
            writes.append(("T", novos_valores["Ocorrência (observações)"]))
        if "Interferente?" in novos_valores:
            writes.append(("V", novos_valores["Interferente?"]))
        if "Situação" in novos_valores:
            writes.append(("W", novos_valores["Situação"]))

        for col_letter, value in writes:
            aba.update_cell(row_idx, _col_to_index(col_letter), value)

        return "Alterações salvas na 'Abordagem'."
    except Exception as e:
        return f"Erro ao atualizar 'Abordagem' (ID={id_h}): {e}"

# =================== INSERÇÕES ===================
def inserir_emissao_I_W(_client, dados_formulario: Dict[str, str]) -> bool:
    """
    Grava na 1ª linha onde a COLUNA M estiver vazia, na aba 'Abordagem' (H..W).
    """
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet("Abordagem")

        row = _first_row_where_col_empty(aba, "M", start_row=2)
        next_id = _next_sequential_id(aba, col_letter="H", start_row=2)

        dia_val = dados_formulario.get("Dia", "")
        if hasattr(dia_val, "strftime"):
            dia_val = dia_val.strftime("%d/%m/%Y")
        hora_val = dados_formulario.get("Hora", "")
        if hasattr(hora_val, "strftime"):
            hora_val = hora_val.strftime("%H:%M")

        freq_val = float(dados_formulario.get("Frequência em MHz", 0.0) or 0.0)
        larg_val = float(dados_formulario.get("Largura em kHz", 0.0) or 0.0)

        faixa_val = (dados_formulario.get("Faixa de Frequência", "") or "").strip()
        ute_val = "Sim" if dados_formulario.get("UTE?") else "Não"
        proc_val = (dados_formulario.get("Processo SEI ou ATO UTE", "") or "").strip()
        obs_val = (dados_formulario.get("Observações/Detalhes/Contatos", "") or "").strip()
        resp_val = (dados_formulario.get("Responsável pela emissão", "") or "").strip()
        autoriz  = (dados_formulario.get("Autorizado? (Q)", "") or "").strip()
        situ_val = (dados_formulario.get("Situação", "Pendente") or "Pendente").strip()

        t_concat = f"{obs_val} - {resp_val}" if (obs_val and resp_val) else (obs_val or resp_val)

        if faixa_val == "":
            return False

        vals_I_to_W = [
            "Abordagem",                            # I
            dados_formulario.get("Fiscal", ""),     # J
            dia_val,                                # K
            hora_val,                               # L
            freq_val,                               # M
            larg_val,                               # N
            faixa_val,                              # O
            dados_formulario.get("Identificação",""),   # P
            autoriz,                                # Q
            ute_val,                                # R
            proc_val,                                # S
            t_concat,                               # T
            "",                                     # U
            dados_formulario.get("Interferente?",""),   # V
            situ_val,                               # W
        ]

        aba.update(f"H{row}", [[str(next_id)]], value_input_option="RAW")
        aba.update(f"I{row}:W{row}", [vals_I_to_W], value_input_option="RAW")
        return True

    except Exception as e:
        st.error(f"Erro ao inserir na aba 'Abordagem' (H + I:W):")
        st.exception(e)
        return False

def inserir_bsr_erb(_client, tipo_ocorrencia: str, regiao: str, lat: str, lon: str) -> str:
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet("Abordagem")
        row = _first_empty_row_in_block(aba, "X", "AC")

        if tipo_ocorrencia == "BSR/Jammer":
            aba.update(f"X{row}:Y{row}", [["1", regiao]], value_input_option="USER_ENTERED")
            aba.update(f"AB{row}:AC{row}", [[lat or "", lon or ""]], value_input_option="USER_ENTERED")
        else:
            aba.update(f"Z{row}:AA{row}", [["1", regiao]], value_input_option="USER_ENTERED")
            aba.update(f"AB{row}:AC{row}", [[lat or "", lon or ""]], value_input_option="USER_ENTERED")

        return f"'{tipo_ocorrencia}' incluído com sucesso."
    except gspread.exceptions.WorksheetNotFound:
        return "ERRO: A aba 'Abordagem' não foi encontrada na planilha."
    except Exception as e:
        st.error("Ocorreu um erro ao registrar a ocorrência (BSR/ERB):")
        st.exception(e)
        return "ERRO: Falha ao registrar. Veja os detalhes acima."

# ============== IDENTIFICAÇÃO DINÂMICA (para 2º botão) ==============
@st.cache_data(ttl=3600)
def carregar_opcoes_identificacao(_client):
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba_estacao = planilha.worksheet("RFeye002093 - ANATEL")
        lista_de_listas = aba_estacao.get('AC3:AC9')
        opcoes = [item[0] for item in lista_de_listas if item]
        return opcoes
    except Exception as e:
        st.warning(f"Não é possível carregar 'Identificação da Emissão' (RFeye002093 - ANATEL): {e}")
        return ["Opção não carregada"]

# --- util: carregar qualquer aba como DataFrame (dedup de colunas) ---
def _load_sheet_as_df(client, nome_aba: str) -> pd.DataFrame:
    planilha = client.open_by_url(URL_PLANILHA)
    aba = planilha.worksheet(nome_aba)
    values = aba.get_all_values()
    if not values:
        return pd.DataFrame()
    header, rows = values[0], values[1:]
    df = pd.DataFrame(rows, columns=header)
    df.columns = _dedupe_columns_index(df.columns)
    
    # Filtra linhas que são completamente nulas ou compostas apenas de strings vazias
    df.dropna(how='all', inplace=True)
    if not df.empty:
        df = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]
    
    return df

# --- Busca por texto livre com robustez para a aba PAINEL ---
def _buscar_por_texto_livre(client, termos: str, abas: List[str]) -> pd.DataFrame:
    resultados = []
    termos = termos.strip()
    if not termos:
        return pd.DataFrame()

    for nome in abas:
        try:
            df = _load_sheet_as_df(client, nome)
            if df.empty:
                continue

            # CORREÇÃO FINAL: Filtro mais rigoroso para remover linhas de "template"
            # Uma linha é considerada um registro válido se tiver dados em "Fiscal" ou "Ocorrência".
            key_fields_for_validation = [
                "Fiscal", "Ocorrência (obsevações)", "Observações/Detalhes/Contatos"
            ]

            available_validation_keys = []
            for key in key_fields_for_validation:
                for col in df.columns:
                    # Inclui nomes de colunas exatos e duplicados (ex: "Fiscal", "Fiscal.1")
                    if col == key or col.startswith(key + "."):
                        available_validation_keys.append(col)
            
            # Remove duplicatas da lista de colunas a serem verificadas
            available_validation_keys = list(dict.fromkeys(available_validation_keys))

            df_to_search = df.copy()
            if available_validation_keys:
                # Mantém apenas as linhas que têm algum valor em pelo menos uma das colunas chave
                mask_has_data = df[available_validation_keys].apply(
                    lambda row: any(_safe_str(v) != "" for v in row),
                    axis=1
                )
                df_to_search = df[mask_has_data]

            if df_to_search.empty:
                continue

            # Lógica de busca: busca em todas as colunas de texto relevantes do DF pré-filtrado.
            relevantes = [col for col in df_to_search.columns if col and isinstance(col, str)]
            if not relevantes:
                continue

            df_busca = df_to_search[relevantes].fillna('').astype(str)
            combinado = df_busca.agg(" | ".join, axis=1)
            mask = _contains_norm(combinado, termos)

            achados = df_to_search[mask].copy()
            if achados.empty:
                continue

            achados.insert(0, "Aba/Origem", nome)
            resultados.append(achados)

        except gspread.exceptions.WorksheetNotFound:
            continue
        except Exception:
            continue

    if not resultados:
        return pd.DataFrame()

    res_final = pd.concat(resultados, ignore_index=True)
    
    # Limpeza final para garantir
    res_final.dropna(how='all', inplace=True)
    if not res_final.empty:
        cols_to_check = [c for c in res_final.columns if c != 'Aba/Origem']
        res_final = res_final[~res_final[cols_to_check].apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]

    return res_final

# --- Botão Voltar centralizado ([2,2,2]) ---
def botao_voltar(label="⬅️ Voltar ao Menu", key=None):
    left, center, right = st.columns([2, 2, 2])
    with center:
        return st.button(label, use_container_width=True, key=key)

# --- Renderização "somente leitura" (mesmo layout da tela de tratar) ---
def render_ocorrencia_readonly(row: pd.Series, key_prefix: str):
    # Helper para buscar valor em colunas normais e duplicadas (ex: 'Data' e 'Data.1')
    def _get_val(keys):
        for k in keys:
            if k in row:
                val = _safe_str(row.get(k))
                if val:
                    return val
        return ""

    id_sel      = _get_val(["ID", "ID.1"])
    local_map   = _get_val(["Local", "Local/Região", "Estação", "Estação.1"])
    fiscal      = _get_val(["Fiscal", "Fiscal.1"])
    data_txt    = _get_val(["Data", "Data.1", "DD/MM/AAAA"])
    hora_txt    = _get_val(["HH:mm", "HH:mm.1"])
    freq_txt    = _get_val(["Frequência (MHz)", "Frequência (MHz).1", "Frequência"])
    bw_txt      = _get_val(["Largura (kHz)", "Largura (kHz).1", "Largura"])
    faixa_env   = _get_val(["Faixa de Frequência Envolvida", "Faixa de Frequência Envolvida.1", "Faixa de Frequência"])
    ident_atual = _get_val(["Identificação", "Identificação.1"])
    autz_atual  = _get_val(["Autorizado?", "Autorizado?.1", "Autorizado? (Q)"])
    ute_atual   = _get_val(["UTE?", "UTE?.1"])
    proc_sei    = _get_val(["Processo SEI UTE", "Processo SEI UTE.1", "Processo SEI ou ATO UTE"])
    obs_txt     = _get_val(["Ocorrência (obsevações)", "Ocorrência (obsevações).1", "Observações/Detalhes/Contatos"])
    ciente_txt  = _get_val(["Alguém mais ciente?", "Alguém mais ciente?.1"])
    interf_at   = _get_val(["Interferente?", "Interferente?.1"])
    situ_atual  = _get_val(["Situação", "Situação.1"])


    colA, colB = st.columns(2)
    with colA:
        st.text_input("ID", value=id_sel, disabled=True, key=f"{key_prefix}_id")
        st.text_input("Estação utilizada", value=local_map, disabled=True, key=f"{key_prefix}_estacao")
        st.text_input("Fiscal", value=fiscal, disabled=True, key=f"{key_prefix}_fiscal")
        st.text_input("Data da identificação", value=data_txt, disabled=True, key=f"{key_prefix}_data")
        st.text_input("HH:mm", value=hora_txt, disabled=True, key=f"{key_prefix}_hora")
        st.text_input("Frequência (MHz)", value=freq_txt, disabled=True, key=f"{key_prefix}_freq")
        st.text_input("Largura (kHz)", value=bw_txt, disabled=True, key=f"{key_prefix}_largura")
        st.text_input("Faixa de Frequência Envolvida", value=faixa_env, disabled=True, key=f"{key_prefix}_faixa")

    with colB:
        ident_idx = IDENT_OPCOES.index(ident_atual) if ident_atual in IDENT_OPCOES else 0
        st.selectbox(f"Identificação {OBRIG}", options=IDENT_OPCOES, index=ident_idx, disabled=True, key=f"{key_prefix}_ident")

        opts_autz = ["Sim", "Não", "Indefinido"]
        idx_autz = opts_autz.index(autz_atual) if autz_atual in opts_autz else 2
        st.selectbox(f"Autorizado? {OBRIG}", options=opts_autz, index=idx_autz, disabled=True, key=f"{key_prefix}_autz")

        ute_val = (str(ute_atual).strip().lower() in ("sim","true","1","x","ok"))
        st.checkbox("UTE?", value=ute_val, disabled=True, key=f"{key_prefix}_ute")

        st.text_input("Processo SEI UTE (ou Ato UTE)", value=proc_sei, disabled=True, key=f"{key_prefix}_procsei")
        st.text_area("Ocorrência (obsevações)", value=obs_txt, disabled=True, key=f"{key_prefix}_obs")

        st.text_input("Alguém mais ciente?", value=ciente_txt, disabled=True, key=f"{key_prefix}_ciente")
        opts_interf = ["Sim", "Não", "Indefinido"]
        idx_interf = opts_interf.index(interf_at) if interf_at in opts_interf else 2
        st.selectbox(f"Interferente? {OBRIG}", options=opts_interf, index=idx_interf, disabled=True, key=f"{key_prefix}_interf")

        opts_situ = ["Pendente", "Concluído"]
        idx_situ = opts_situ.index(situ_atual) if situ_atual in opts_situ else 0
        st.selectbox(f"Situação {OBRIG}", options=opts_situ, index=idx_situ, disabled=True, key=f"{key_prefix}_situ")

# ========================= TELAS =========================
def tela_menu_principal():
    render_header()
    st.divider()

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        _, button_col, _ = st.columns([0.5, 9, 0.5])
        with button_col:
            # Âncora invisível para o CSS encontrar e estilizar os 3 botões seguintes
            st.markdown('<div id="marker-vermelho"></div>', unsafe_allow_html=True)

            if st.button("**📋 INSERIR** emissão verificada em campo", use_container_width=True, key="btn_inserir"):
                st.session_state.view = 'inserir'; st.rerun()

            if st.button("**📝 TRATAR** emissões pendentes", use_container_width=True, key="btn_consultar"):
                st.session_state.view = 'consultar'; st.rerun()

            if st.button("**📵 REGISTRAR** Jammer ou ERB Fake", use_container_width=True, key="btn_bsr"):
                st.session_state.view = 'bsr_erb'; st.rerun()

            if st.button("**🔎 PESQUISAR** dados de emissões", use_container_width=True, key="btn_buscar"):
                st.session_state.view = 'busca'; st.rerun()

            if st.button("🗒️ **CONSULTAR** Atos de UTE", use_container_width=True, key="btn_ute"):
                st.session_state.view = 'tabela_ute'; st.rerun()
            
            st.link_button("🗺️ **Mapa das Estações**", MAPS_URL, use_container_width=True)
            st.link_button("🌍 **Tradutor de Voz**", "https://translate.google.com/?sl=auto&tl=pt&op=translate", use_container_width=True)

def tela_consultar(client):
    render_header()
    st.divider()

    st.markdown('<div class="info-green">Consulte as emissões pendentes de identificação para verificação em campo (em caso de sucesso, alterar Situação de Pendente para Concluído<br>(Sugestão: verifique por região)</div>', unsafe_allow_html=True)

    df_painel = carregar_pendencias_painel_mapeadas(client)
    df_abord  = carregar_pendencias_abordagem_pendentes(client)
    if not df_painel.empty and not df_abord.empty:
        df_pend = pd.concat([df_painel, df_abord], ignore_index=True)
    elif not df_painel.empty:
        df_pend = df_painel
    else:
        df_pend = df_abord

    if df_pend is not None and not df_pend.empty:
        opcoes = [
            f"{row['Local']} | {row['Data']} | {row['Frequência (MHz)']} MHz | {row['Largura (kHz)']} kHz | {row['Ocorrência (observações)']} | {row['ID']}"
            for _, row in df_pend.iterrows()
        ]
        selecionado = st.selectbox(
            "Selecione a emissão para tratamento:",
            options=opcoes,
            index=None,
            placeholder="Região | Data da ident | Frequência | Largura | Obs | ID (Estação)"
        )

        if selecionado:
            idx = opcoes.index(selecionado)
            registro = df_pend.iloc[idx]

            id_sel      = str(registro.get("ID", ""))
            estacao_raw = str(registro.get("EstacaoRaw", ""))
            fiscal      = str(registro.get("Fiscal", ""))
            data_txt    = str(registro.get("Data", ""))
            hora_txt    = str(registro.get("HH:mm", ""))
            freq_txt    = str(registro.get("Frequência (MHz)", ""))
            bw_txt      = str(registro.get("Largura (kHz)", ""))
            local_map   = str(registro.get("Local", ""))
            faixa_env   = str(registro.get("Faixa de Frequência Envolvida", ""))
            ident_atual = str(registro.get("Identificação", ""))
            autz_atual  = str(registro.get("Autorizado?", ""))
            ute_atual   = str(registro.get("UTE?", ""))
            proc_sei    = str(registro.get("Processo SEI UTE", ""))
            obs_txt     = str(registro.get("Ocorrência (observações)", ""))
            ciente_txt  = str(registro.get("Alguém mais ciente?", ""))
            interf_at   = str(registro.get("Interferente?", ""))
            situ_atual  = str(registro.get("Situação", "Pendente"))
            fonte       = str(registro.get("Fonte", "PAINEL"))

            st.markdown("#### Editar ocorrência selecionada")
            with st.form("form_editar_pendente", clear_on_submit=False):
                colA, colB = st.columns(2)
                with colA:
                    st.text_input("ID", value=id_sel, disabled=True)
                    st.text_input("Estação utilizada", value=local_map, disabled=True)
                    st.text_input("Fiscal", value=fiscal, disabled=True)
                    st.text_input("Data da identificação", value=data_txt, disabled=True)
                    st.text_input("HH:mm", value=hora_txt, disabled=True)
                    st.text_input("Frequência (MHz)", value=freq_txt, disabled=True)
                    st.text_input("Largura (kHz)", value=bw_txt, disabled=True)
                    st.text_input("Faixa de Frequência Envolvida", value=faixa_env, disabled=True)

                with colB:
                    ident_edit = st.selectbox(f"Identificação {OBRIG}", options=IDENT_OPCOES, index=IDENT_OPCOES.index(ident_atual) if ident_atual in IDENT_OPCOES else 0)
                    autz_edit  = st.selectbox(f"Autorizado? {OBRIG}", options=["Sim", "Não", "Indefinido"], index=["Sim","Não","Indefinido"].index(autz_atual) if autz_atual in ["Sim","Não","Indefinido"] else 2)
                    ute_check  = st.checkbox("UTE? ", value=(ute_atual.strip().lower() in ("sim","true","1","x","ok")))
                    proc_edit  = st.text_input("Processo SEI UTE (ou Ato UTE)", value=proc_sei)
                    obs_edit   = st.text_area("Ocorrência (obsevações)", value=obs_txt)
                    ciente_edit= st.text_input("Alguém mais ciente?", value=ciente_txt)
                    interf_edit= st.selectbox(f"Interferente? {OBRIG}", options=["Sim","Não","Indefinido"], index=["Sim","Não","Indefinido"].index(interf_at) if interf_at in ["Sim","Não","Indefinido"] else 2)
                    situ_edit  = st.selectbox(f"Situação {OBRIG}", options=["Pendente","Concluído"], index=["Pendente","Concluído"].index(situ_atual) if situ_atual in ["Pendente","Concluído"] else 0)

                colL, colC, colR = st.columns([3, 4, 3])
                with colC:
                    submitted = st.form_submit_button("Salvar alterações", use_container_width=True)

                if submitted:
                    erros = []
                    if not ident_edit: erros.append("Identificação")
                    if not autz_edit:  erros.append("Autorizado?")
                    if not interf_edit: erros.append("Interferente?")
                    if not situ_edit:  erros.append("Situação")
                    if ute_check and not proc_edit.strip():
                        erros.append("Processo SEI UTE (ou Ato UTE)")

                    if erros:
                        st.error("Campos obrigatórios: " + ", ".join(erros))
                    else:
                        pac = {
                            "estacao_raw": estacao_raw,
                            "id_sel": id_sel,
                            "fonte": fonte,
                            "novos": {
                                "Identificação": ident_edit,
                                "Autorizado?": autz_edit,
                                "UTE?": "Sim" if ute_check else "Não",
                                "Processo SEI UTE": proc_edit,
                                "Ocorrência (observações)": obs_edit,
                                "Alguém mais ciente?": ciente_edit,
                                "Interferente?": interf_edit,
                                "Situação": situ_edit,
                            }
                        }
                        msgs = []
                        if pac["fonte"] == "PAINEL":
                            r1 = atualizar_campos_na_aba_mae(client, pac["estacao_raw"], pac["id_sel"], pac["novos"]); msgs.append(r1)
                        elif pac["fonte"] == "ABORDAGEM":
                            r2 = atualizar_campos_abordagem_por_id(client, pac["id_sel"], pac["novos"]); msgs.append(r2)
                        mix = " | ".join(msgs) if msgs else "Alterações processadas."
                        if any("ERRO" in m for m in msgs): st.error(mix)
                        else: st.success(mix)

    else:
        st.success("✔️ Nenhuma emissão pendente de identificação no momento.")

    if botao_voltar():
        st.session_state.view = 'main_menu'
        st.rerun()

def tela_inserir(client):
    render_header()
    st.divider()

    opcoes_identificacao = carregar_opcoes_identificacao(client)
    with st.form("form_nova_emissao", clear_on_submit=False):
        fuso_horario_gmt3 = ZoneInfo("America/Sao_Paulo")
        hora_padrao = datetime.now(fuso_horario_gmt3).time().replace(second=0, microsecond=0)
        dados = {
            'Dia': st.date_input(f"Data {OBRIG}"),
            'Hora': st.time_input(f"Hora {OBRIG}", value=hora_padrao),
            'Fiscal': st.text_input(f"Fiscal Responsável {OBRIG}"),
            'Local/Região': st.text_input("Local/Região"),
            'Frequência em MHz': st.number_input(f"Frequência (MHz) {OBRIG}", format="%.3f", step=0.001, min_value=0.0),
            'Largura em kHz': st.number_input(f"Largura (kHz) {OBRIG}", format="%.1f", step=0.1, min_value=0.0),
            'Faixa de Frequência': st.selectbox(f"Faixa de Frequência {OBRIG}", options=FAIXA_OPCOES, index=None, placeholder="Selecione..."),
            'Identificação': st.selectbox(f"Identificação da Emissão {OBRIG}", options=opcoes_identificacao, index=None, placeholder="Selecione..."),
            'Autorizado? (Q)': st.selectbox(f"Autorizado? {OBRIG}", options=["Sim", "Não", "Não licenciável"], index=None, placeholder="Selecione..."),
            'Responsável pela emissão': st.text_input("Responsável pela emissão (Pessoa ou Empresa)"),
            'Interferente?': st.selectbox(f"Interferente? {OBRIG}", ("Sim", "Não", "Indefinido"), index=None, placeholder="Selecione..."),
            'UTE?': st.checkbox("UTE?"),
            'Processo SEI ou ATO UTE': st.text_input("Processo SEI ou ATO UTE"),
            'Observações/Detalhes/Contatos': st.text_area(f"Observações/Detalhes/Contatos {OBRIG}"),
            'Situação': st.selectbox(f"Situação {OBRIG}", options=["Pendente", "Concluída"], index=0),
        }

        colL, colC, colR = st.columns([3, 4, 3])
        with colC:
            submitted = st.form_submit_button("Registrar Emissão", use_container_width=True)

        if submitted:
            erros = []
            if not dados['Fiscal'].strip(): erros.append("Fiscal Responsável")
            if (dados['Frequência em MHz'] is None) or (dados['Frequência em MHz'] <= 0): erros.append("Frequência (MHz) > 0")
            if (dados['Largura em kHz'] is None) or (dados['Largura em kHz'] <= 0): erros.append("Largura em kHz > 0")
            if not dados['Faixa de Frequência']: erros.append("Faixa de Frequência")
            if dados['Identificação'] is None: erros.append("Identificação da Emissão")
            if dados['Autorizado? (Q)'] is None: erros.append("Autorizado?")
            if dados['Interferente?'] is None: erros.append("Interferente?")
            if dados['UTE?'] and not dados['Processo SEI ou ATO UTE'].strip(): erros.append("Processo SEI ou ATO UTE")
            if not dados['Observações/Detalhes/Contatos'].strip(): erros.append("Observações/Detalhes/Contatos")
            if not dados['Situação']: erros.append("Situação")

            if erros:
                st.error("Campos obrigatórios: " + ", ".join(erros))
            else:
                dados['Dia'] = dados['Dia'].strftime('%d/%m/%Y')
                with st.spinner("Registrando..."):
                    ok = inserir_emissao_I_W(client, dados)
                if ok:
                    st.success("Nova emissão registrada com sucesso")
                else:
                    st.error("Falha ao registrar. Verifique os campos obrigatórios (especialmente Faixa de Frequência).")

    if botao_voltar(key="voltar_inserir"):
        st.session_state.view = 'main_menu'; st.rerun()

def tela_bsr_erb(client):
    render_header()
    st.divider()

    with st.form("form_bsr_erb"):
        tipo = st.radio(label=f"Selecione o tipo de ocorrência: {OBRIG}", options=('BSR/Jammer', 'ERB Fake'), index=None, horizontal=True)
        regiao = st.text_input(f"Local/Região da ocorrência: {OBRIG}")
        lat = st.text_input("Latitude (formato: -N.NNNNNN)")
        lon = st.text_input("Longitude (formato: -N.NNNNNN)")

        colL, colC, colR = st.columns([3, 4, 3])
        with colC:
            submitted = st.form_submit_button("Registrar Ocorrência", use_container_width=True)

        if submitted:
            faltas = []
            if tipo is None: faltas.append("Tipo de ocorrência")
            if not regiao.strip(): faltas.append("Local/Região da ocorrência")

            coord_erros = []
            if not _valid_neg_coord(lat): coord_erros.append("Latitude (use o padrão -1.234567)")
            if not _valid_neg_coord(lon): coord_erros.append("Longitude (use o padrão -48.123456)")
            if coord_erros: st.error("Erro nas coordenadas: " + " | ".join(coord_erros))

            if faltas:
                st.error("Campos obrigatórios: " + ", ".join(faltas))
            elif not coord_erros:
                with st.spinner("Registrando..."):
                    resultado = inserir_bsr_erb(client, tipo, regiao, lat, lon)
                if "ERRO" in resultado: st.error(resultado)
                else: st.success(resultado)

    if botao_voltar(key="voltar_bsr_erb"):
        st.session_state.view = 'main_menu'; st.rerun()

# ======================= TELA: BUSCA =======================
def tela_busca(client):
    render_header()
    st.divider()

    st.markdown('<div class="info-green">Consulta por texto livre em quaisquer campos (frequência, nomes, telefones etc.).</div>', unsafe_allow_html=True)

    termo = st.text_input("Digite o texto para consultar (mín. 3 caracteres):", value="")
    opcoes_abas = ["PAINEL", "Abordagem"] + TODAS_ABAS_RFEYE
    sel_abas = st.multiselect("Escolha as abas onde consultar (padrão: todas):", options=opcoes_abas, default=opcoes_abas)

    colL, colC, colR = st.columns([3,4,3])
    with colC:
        acionar = st.button("Consultar", use_container_width=True)

    if acionar:
        if len(termo.strip()) < 3:
            st.warning("Digite pelo menos 3 caracteres para consultar.")
        else:
            with st.spinner("Procurando..."):
                df_res = _buscar_por_texto_livre(client, termo.strip(), sel_abas)
            if df_res.empty:
                st.info("Nenhum resultado encontrado para sua consulta.")
            else:
                st.success(f"Resultados encontrados: {len(df_res)}")

                for i, (_, row) in enumerate(df_res.iterrows(), start=1):
                    cabecalho = []
                    aba_origem = row.get("Aba/Origem")

                    # Título customizado para a aba "Abordagem"
                    if aba_origem == "Abordagem":
                        cabecalho.append("Abordagem")
                        
                        data = _safe_str(row.get("Data.1", row.get("Data")))
                        if data: cabecalho.append(data)
                        
                        freq = _safe_str(row.get("Frequência (MHz).1", row.get("Frequência (MHz)")))
                        if freq: cabecalho.append(f"{freq} MHz")
                        
                        ident = _safe_str(row.get("Identificação.1", row.get("Identificação")))
                        if ident: cabecalho.append(ident)

                        situ = _safe_str(row.get("Situação.1", row.get("Situação")))
                        if situ: cabecalho.append(situ)
                    
                    # Título padrão para as outras abas
                    else:
                        loc = _safe_str(row.get("Local", ""))
                        if not loc:
                            loc = _safe_str(row.get("Local/Região", row.get("Estação","")))
                        if loc: cabecalho.append(loc)

                        data = _safe_str(row.get("Data", row.get("Dia","")))
                        if data: cabecalho.append(data)

                        freq = _safe_str(row.get("Frequência (MHz)", row.get("Frequência","")))
                        if freq: cabecalho.append(f"{freq} MHz")

                        idv = _safe_str(row.get("ID", ""))
                        if idv: cabecalho.append(f"ID {idv}")

                    titulo = " | ".join(cabecalho) if cabecalho else f"Resultado #{i} ({aba_origem})"

                    with st.expander(titulo, expanded=False):
                        key_prefix = f"busca_{i}_{row.get('ID','semid')}"
                        render_ocorrencia_readonly(row, key_prefix=key_prefix)

    if botao_voltar(key="voltar_busca"):
        st.session_state.view = 'main_menu'; st.rerun()

# ======================= TELA: Tabela UTE =======================
def tela_tabela_ute(client):
    render_header()
    st.divider()
    st.markdown("#### Atos de UTE - COP30")
    st.markdown("<p style='text-align: center; font-size: small; margin-top: -0.5rem; margin-bottom: 0.5rem;'>(gire o celular ⟳)</p>", unsafe_allow_html=True)


    # Injeta o JavaScript para a funcionalidade de copiar
    st.markdown("""
    <script>
    function copyToClipboard(text, element) {
        // Fallback para ambientes não seguros
        const el = document.createElement('textarea');
        el.value = text;
        el.style.position = 'absolute';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        el.select();
        try {
            var successful = document.execCommand('copy');
            var msg = successful ? 'Copiado! ✔️' : 'Falhou!';
            element.innerHTML = msg;
        } catch (err) {
            element.innerHTML = 'Falhou!';
        }
        document.body.removeChild(el);
        setTimeout(() => { element.innerHTML = text; }, 1500);
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Injeta CSS para a tabela
    st.markdown("""
    <style>
        .ute-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }
        .ute-table th, .ute-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }
        .ute-table th {
            background-color: #f2f2f2;
            color: #333;
        }
        .copyable-cell {
            cursor: pointer;
            color: #14337b;
            font-weight: bold;
            -webkit-tap-highlight-color: transparent; /* Remove o brilho azul no clique mobile */
        }
        .copyable-cell:hover {
            text-decoration: underline;
            background-color: #f0f0f0;
        }
    </style>
    """, unsafe_allow_html=True)

    df_ute = carregar_dados_ute(client)

    if not df_ute.empty:
        # Constrói a tabela HTML
        html = "<table class='ute-table'><thead><tr><th>País</th><th>Frequência (MHz)</th><th>Largura (kHz)</th><th>Processo SEI</th></tr></thead><tbody>"
        for _, row in df_ute.iterrows():
            processo_sei = _safe_str(row['Processo SEI'])
            html += "<tr>"
            html += f"<td>{_safe_str(row['País'])}</td>"
            html += f"<td>{_safe_str(row['Frequência (MHz)'])}</td>"
            html += f"<td>{_safe_str(row['Largura (kHz)'])}</td>"
            html += f"<td class='copyable-cell' onclick='copyToClipboard(\"{processo_sei}\", this)'>{processo_sei}</td>"
            html += "</tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nenhum dado de Ato UTE encontrado ou a tabela está vazia.")

    # Botões SEI
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("SEI Interno", "https://sei.anatel.gov.br", use_container_width=True)
    with col2:
        st.link_button("SEI Público", "https://sei.anatel.gov.br/sei/modulos/pesquisa/md_pesq_processo_pesquisar.php?acao_externa=protocolo_pesquisar&acao_origem_externa=protocolo_pesquisar&id_orgao_acesso_externo=0", use_container_width=True)

    st.write("") # Adiciona um espaço antes do botão voltar
    if botao_voltar(key="voltar_ute"):
        st.session_state.view = 'main_menu'
        st.rerun()

# =========================== MAIN ===========================
try:
    client = get_gspread_client()
    if 'view' not in st.session_state: st.session_state.view = 'main_menu'
    if st.session_state.view == 'main_menu':
        tela_menu_principal()
    elif st.session_state.view == 'consultar':
        tela_consultar(client)
    elif st.session_state.view == 'inserir':
        tela_inserir(client)
    elif st.session_state.view == 'bsr_erb':
        tela_bsr_erb(client)
    elif st.session_state.view == 'busca':
        tela_busca(client)
    elif st.session_state.view == 'tabela_ute':
        tela_tabela_ute(client)
except Exception as e:
    st.error("Erro fatal de autenticação ou inicialização. Verifique os seus segredos (secrets.toml).")

    st.exception(e)



