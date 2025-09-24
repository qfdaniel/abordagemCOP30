import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import re
import base64
from pathlib import Path
from typing import Optional

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Abordagem - COP30",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTE GLOBAL COM O LINK DA PLANILHA ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1b2GOAOIN6mvgLH1rpvRD1vF4Ro9VOqylKkXaUTAq0Ro/edit"

# --- MAPEAMENTO RFeye -> LOCAL (região) ---
MAPEAMENTO_CODIGO = {
    "RFeye002093": "Anatel",
    "RFeye002303": "Parque da Cidade",
    "RFeye002315": "Docas",
    "RFeye002012": "Terminal de Outeiro",
    "RFeye002175": "Aldeia",
    "RFeye002129": "Mangueirinho",
}

# Opções fixas de Identificação (edição)
IDENT_OPCOES = [
    "Sinal de dados",
    "Comunicação (voz) relacionada ao evento",
    "Comunicação (voz) não relacionada ao evento",
    "Sinal não relacionado ao evento",
    "Espúrio ou Produto de Intermodulação",
    "Ruído",
    "Não identificado",
]

# --- UTILITÁRIOS PARA LOGO (BASE64) ---
def _img_b64(path: str) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")

def render_header(titulo: str, esquerda: str = "logo.png", direita: str = "anatel.png"):
    left_b64  = _img_b64(esquerda)
    right_b64 = _img_b64(direita)
    left_tag  = f'<img src="data:image/png;base64,{left_b64}" alt="Logo esquerda">' if left_b64 else ""
    right_tag = f'<img src="data:image/png;base64,{right_b64}" alt="Logo direita">' if right_b64 else ""
    st.markdown(
        f"""
        <div class="header-logos">
            {left_tag}
            <h2>{titulo}</h2>
            {right_tag}
        </div>
        """,
        unsafe_allow_html=True
    )

# --- CSS CUSTOMIZADO ---
st.markdown("""
<style>
    /* Painel central mais estreito */
    .block-container {
      max-width: 760px;       /* ajuste aqui se quiser mais estreito/largo */
      padding-top: 0.75rem;
      padding-bottom: 0.75rem;
      margin: 0 auto;
    }

    .stApp { background-color: #D7D6D4; }
    #MainMenu, footer, header { visibility: hidden; }
    div[data-testid="stDivider"] { margin-top: -1.5rem !important; }

    /* Cabeçalho responsivo (logos + título) */
    .header-logos {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      flex-wrap: wrap;
      text-align: center;
      margin-bottom: 0.5rem;
    }
    .header-logos img { height: 56px; }
    .header-logos h2 {
      margin: 0;
      color: #1A311F;
      font-weight: 700;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
      font-size: 2rem;
    }

    /* Botões padrão (inclui menu e submits) em gradiente azul */
    .stButton>button {
        width: 100%; height: 3.5em; font-size: 1.9em; font-weight: bold; margin-bottom: 10px;
        border-radius: 8px; border: 3.4px solid #54515c;
        background: linear-gradient(to bottom, #14337b, #4464A7); color: white;
        transition: all 0.2s ease-in-out; text-align: center; display: flex; align-items: center; justify-content: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(to bottom, #14337b, #4464A7); color: white; border-color: white;
        box-shadow: 4px 4px 8px rgba(0,0,0,0.4); transform: translateY(-2px);
    }
    .stButton>button p { white-space: pre-wrap; }

    /* Tradutor de Voz (st.link_button) com gradiente verde e mais alto */
    div[data-testid="stLinkButton"] a,
    a[data-testid="stLinkButton"],
    div[data-testid="stLinkButtonContainer"] a,
    a[href*="translate.google.com"] {
        display: flex !important; align-items: center !important; justify-content: center !important;
        width: 100% !important; height: 2.3em !important; font-size: 1.9em !important; font-weight: 800 !important;
        border-radius: 8px !important; border: 3.4px solid #3b6e3c !important;
        background-image: linear-gradient(to bottom, #2e7d32, #66bb6a) !important;
        color: #ffffff !important; text-decoration: none !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3) !important; transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stLinkButton"] a:hover,
    a[data-testid="stLinkButton"]:hover,
    div[data-testid="stLinkButtonContainer"] a:hover,
    a[href*="translate.google.com"]:hover {
        background-image: linear-gradient(to bottom, #2e7d32, #81c784) !important;
        border-color: #ffffff !important; transform: translateY(-2px) !important;
        box-shadow: 4px 4px 8px rgba(0,0,0,0.4) !important; color: #ffffff !important;
    }

    .confirm-warning {
        background: linear-gradient(to bottom, #d9534f, #c9302c);
        color: white; font-weight: bold; text-align: center; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;
    }

    .details-card { background-color: #f0f2f6; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-top: 15px; margin-bottom: 15px; }
    .details-card h4 { color: #1A311F; margin-bottom: 10px; }
    .details-card p { font-size: 1.1em; line-height: 1.6; }

    /* Submits de forms no mesmo gradiente azul */
    div[aria-label="form_nova_emissao"] .stButton > button,
    form[aria-label="form_nova_emissao"] .stButton > button,
    div[aria-label="form_bsr_erb"] .stButton > button,
    form[aria-label="form_bsr_erb"] .stButton > button,
    form[aria-label="form_editar_pendente"] .stButton > button {
        background: linear-gradient(to bottom, #14337b, #4464A7); color: #FFFFFF; font-weight: bold;
        border: 3.4px solid #54515c; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    form[aria-label="form_editar_pendente"] .stButton > button:hover,
    form[aria-label="form_nova_emissao"] .stButton > button:hover,
    form[aria-label="form_bsr_erb"] .stButton > button:hover {
        background: linear-gradient(to bottom, #14337b, #4464A7); color: #FFFFFF; border-color: #FFFFFF;
        box-shadow: 4px 4px 8px rgba(0,0,0,0.4); transform: translateY(-2px);
    }

    /* Mobile tweaks */
    @media (max-width: 640px) {
      .block-container { max-width: 100%; padding: 0.5rem 0.75rem; }
      .header-logos { gap: 8px; }
      .header-logos img { height: 40px; }
      .header-logos h2 { font-size: 1.5rem; }
      .stButton > button { height: 3.2em; font-size: 1.3em; }
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM GOOGLE SHEETS (GSPREAD) ---
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    scoped_creds = creds.with_scopes([
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    return gspread.authorize(scoped_creds)

# --- UTILITÁRIOS ---
def _first_col_match(columns, *preds):
    for c in columns:
        s = c.strip().lower()
        for p in preds:
            if p(s):
                return c
    return None

def _extract_rfeye_code(estacao_str: str) -> str:
    """Extrai 'RFeyeNNNNNN' de 'RFeye002093 - ANATEL'."""
    if not estacao_str:
        return ""
    m = re.search(r"(RFeye\\d{6})", estacao_str, flags=re.IGNORECASE)
    return m.group(1) if m else ""

def _map_local_by_estacao(estacao_str: str) -> str:
    code = _extract_rfeye_code(estacao_str)
    if code:
        return MAPEAMENTO_CODIGO.get(code, estacao_str)
    return estacao_str

@st.cache_data(ttl=60)
def carregar_pendencias_painel_mapeadas(_client):
    """
    Lê 'PAINEL', filtra Situação == 'Pendente' e retorna DF:
    Local(mapeado por código RFeye em Estação), Data, Frequência (MHz),
    Largura (kHz), Ocorrências (observações), ID, EstacaoRaw, Identificação.
    """
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba_painel = planilha.worksheet("PAINEL")
        valores = aba_painel.get_all_values()
        if len(valores) < 2:
            return pd.DataFrame()

        header = valores[0]
        rows = valores[1:]
        df = pd.DataFrame(rows, columns=header)

        col_situacao = _first_col_match(df.columns, lambda s: s == "situação", lambda s: s == "situacao")
        col_estacao  = _first_col_match(df.columns, lambda s: "estação" in s, lambda s: "estacao" in s)
        col_data     = _first_col_match(df.columns, lambda s: s == "data", lambda s: s == "dia")
        col_freq     = _first_col_match(df.columns, lambda s: "frequência" in s, lambda s: "frequencia" in s)
        col_larg     = _first_col_match(df.columns, lambda s: "largura" in s)
        col_obs      = _first_col_match(df.columns, lambda s: "observa" in s)
        col_id       = _first_col_match(df.columns, lambda s: s == "id")
        col_ident    = _first_col_match(df.columns, lambda s: "identificação" in s, lambda s: "identificacao" in s)

        if not (col_situacao and col_estacao and col_id):
            return pd.DataFrame()

        situ = df[col_situacao].astype(str).str.strip().str.lower()
        pend = df[situ.eq("pendente")].copy()
        if pend.empty:
            return pd.DataFrame()

        out = pd.DataFrame()
        out["Local"] = pend[col_estacao].map(_map_local_by_estacao)
        out["EstacaoRaw"] = pend[col_estacao]
        out["Data"] = pend[col_data] if col_data else ""
        out["Frequência (MHz)"] = pend[col_freq] if col_freq else ""
        out["Largura (kHz)"] = pend[col_larg] if col_larg else ""
        out["Ocorrências (observações)"] = pend[col_obs] if col_obs else ""
        out["ID"] = pend[col_id]
        out["Identificação"] = pend[col_ident] if col_ident else ""

        out = out.sort_values(by=["Local", "Data"], kind="stable", na_position="last").reset_index(drop=True)
        return out

    except Exception as e:
        st.error("Erro ao carregar pendências da aba 'PAINEL'.")
        st.exception(e)
        return pd.DataFrame()

def _parse_data_ddmmyyyy(s):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return date.today()

def _find_header_col_index(header_list, *preds):
    for idx, name in enumerate(header_list, start=1):
        s = (name or "").strip().lower()
        for p in preds:
            if p(s):
                return idx
    return None

def atualizar_campos_na_aba_mae(_client, estacao_raw, id_ocorrencia, novos_valores):
    """
    Atualiza, na aba RFeyeXXXXX indicada por 'estacao_raw', a linha cujo ID (col A) == id_ocorrencia.
    novos_valores pode conter: 'Situação', 'Data', 'Ocorrências (observações)', 'Identificação'.
    (Frequência/Largura estão bloqueadas na edição e não são atualizadas aqui.)
    """
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba = planilha.worksheet(estacao_raw)
    except gspread.exceptions.WorksheetNotFound:
        return f"ERRO: Aba mãe '{estacao_raw}' não encontrada."
    except Exception as e:
        return f"ERRO ao abrir planilha: {e}"

    try:
        header = aba.row_values(1)
        cell = aba.find(str(id_ocorrencia), in_column=1)  # ID na coluna A
        if not cell:
            return f"ERRO: ID {id_ocorrencia} não encontrado na aba '{estacao_raw}'."

        row_idx = cell.row

        col_situ = _find_header_col_index(header, lambda s: s == "situação", lambda s: s == "situacao")
        col_data = _find_header_col_index(header, lambda s: s == "data", lambda s: s == "dia")
        col_obs  = _find_header_col_index(header, lambda s: "observa" in s)
        col_ident= _find_header_col_index(header, lambda s: "identificação" in s, lambda s: "identificacao" in s)

        if col_situ is None:
            col_situ = 16  # fallback: coluna P

        updates = []
        if "Situação" in novos_valores and col_situ:
            updates.append((row_idx, col_situ, novos_valores["Situação"]))
        if "Data" in novos_valores and col_data:
            updates.append((row_idx, col_data, novos_valores["Data"]))
        if "Ocorrências (observações)" in novos_valores and col_obs:
            updates.append((row_idx, col_obs, novos_valores["Ocorrências (observações)"]))
        if "Identificação" in novos_valores and col_ident:
            updates.append((row_idx, col_ident, novos_valores["Identificação"]))

        for r, c, v in updates:
            aba.update_cell(r, c, v)

        return f"Ocorrência {id_ocorrencia} atualizada na aba '{estacao_raw}'."

    except Exception as e:
        return f"ERRO ao atualizar a aba '{estacao_raw}': {e}"

# --- OUTRAS ROTINAS (inserção / BSR-ERB) ---
def inserir_nova_abordagem(_client, dados_formulario):
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba_abordagem = planilha.worksheet("Abordagem")
        valores_formulario = list(dados_formulario.values())
        nova_linha = [''] * 7 + valores_formulario
        aba_abordagem.append_row(nova_linha, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Erro ao inserir dados na aba 'Abordagem': {e}")
        return False

def registrar_bsr_erb(_client, regiao, tipo_ocorrencia, lat, lon):
    try:
        planilha = _client.open_by_url(URL_PLANILHA)
        aba_log = planilha.worksheet("Abordagem")
        todas_as_linhas = aba_log.get_all_values()
        proxima_linha = len(todas_as_linhas) + 1
        if tipo_ocorrencia == 'BSR/Jammer':
            aba_log.update_cell(proxima_linha, 17, 1)  # Q
            aba_log.update_cell(proxima_linha, 18, regiao)  # R
        elif tipo_ocorrencia == 'ERB Fake':
            aba_log.update_cell(proxima_linha, 19, 1)  # S
            aba_log.update_cell(proxima_linha, 20, regiao)  # T
        aba_log.update_cell(proxima_linha, 21, lat)  # U
        aba_log.update_cell(proxima_linha, 22, lon)  # V
        return f"'{tipo_ocorrencia}' incluído com sucesso."
    except gspread.exceptions.WorksheetNotFound:
        return "ERRO: A aba 'Abordagem' não foi encontrada na planilha."
    except Exception as e:
        st.error("Ocorreu um erro ao registrar a ocorrência:")
        st.exception(e)
        return "ERRO: Falha ao registrar. Veja os detalhes acima."

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

# --- Helper: botão "Voltar ao Menu" (proporção [2,2,2]) ---
def botao_voltar(label="⬅️ Voltar ao Menu", key=None):
    left, center, right = st.columns([2, 2, 2])
    with center:
        return st.button(label, use_container_width=True, key=key)

# --- TELAS ---
def tela_menu_principal():
    render_header("Abordagem - COP30")
    st.divider()

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        _, button_col, _ = st.columns([0.5, 9, 0.5])
        with button_col:
            if st.button("CONSULTAR/TRATAR\n emissões pendentes", use_container_width=True):
                st.session_state.view = 'consultar'
                st.rerun()
            if st.button("INSERIR emissão\nverificada em campo", use_container_width=True):
                st.session_state.view = 'inserir'
                st.rerun()
            if st.button("INSERIR ocorrência\nde BSR ou ERB Fake", use_container_width=True):
                st.session_state.view = 'bsr_erb'
                st.rerun()
            st.link_button(
                "Tradutor de Voz",
                "https://translate.google.com/?sl=auto&tl=pt&op=translate",
                use_container_width=True
            )

def tela_consultar(client):
    render_header("Consultar Pendências")
    st.divider()

    st.info("Consulte as emissões pendentes de identificação (Sugestão: Verifique por região)")
    df_pend = carregar_pendencias_painel_mapeadas(client)

    if not df_pend.empty:
        opcoes = [
            f"{row['Local']} | {row['Data']} | {row['Frequência (MHz)']} MHz | "
            f"{row['Largura (kHz)']} kHz | {row['Ocorrências (observações)']} | {row['ID']}"
            for _, row in df_pend.iterrows()
        ]
        selecionado = st.selectbox(
            "Selecione a emissão:",
            options=opcoes,
            index=None,
            placeholder="Clique para escolher..."
        )

        if selecionado:
            idx = opcoes.index(selecionado)
            registro = df_pend.iloc[idx]
            local       = registro["Local"]
            estacao_raw = registro["EstacaoRaw"]
            id_sel      = str(registro["ID"])
            data_atual  = _parse_data_ddmmyyyy(registro["Data"])
            freq_str    = str(registro["Frequência (MHz)"]) if pd.notna(registro["Frequência (MHz)"]) else ""
            larg_str    = str(registro["Largura (kHz)"]) if pd.notna(registro["Largura (kHz)"]) else ""
            obs_atual   = str(registro["Ocorrências (observações)"]) if pd.notna(registro["Ocorrências (observações)"]) else ""
            ident_atual = str(registro["Identificação"]) if "Identificação" in registro and pd.notna(registro["Identificação"]) else ""
            ident_idx   = IDENT_OPCOES.index(ident_atual) if ident_atual in IDENT_OPCOES else IDENT_OPCOES.index("Não identificado")

            st.markdown("#### Editar ocorrência selecionada")
            with st.form("form_editar_pendente", clear_on_submit=False):
                colA, colB = st.columns(2)
                with colA:
                    st.text_input("Local", value=local, disabled=True)
                    st.text_input("Frequência (MHz)", value=freq_str, disabled=True)
                    novo_obs  = st.text_area("Observações (detalhes)", value=obs_atual)
                with colB:
                    nova_data = st.date_input("Data (DD/MM/AAAA)", value=data_atual)
                    st.text_input("Largura (kHz)", value=larg_str, disabled=True)
                    nova_situ = st.selectbox("Situação", ["Pendente", "Concluído"], index=0)

                nova_ident = st.selectbox(
                    "Identificação da emissão",
                    IDENT_OPCOES,
                    index=ident_idx,
                    help="Classificação da emissão conforme enquadramento técnico"
                )

                submitted = st.form_submit_button("Salvar alterações na aba-mãe (RFeye)")
                if submitted:
                    novos = {
                        "Data": nova_data.strftime("%d/%m/%Y"),
                        "Ocorrências (observações)": novo_obs,
                        "Situação": nova_situ,
                        "Identificação": nova_ident,
                    }
                    with st.spinner("Atualizando aba de origem..."):
                        resultado = atualizar_campos_na_aba_mae(client, estacao_raw, id_sel, novos)
                    if "ERRO" in resultado:
                        st.error(resultado)
                    else:
                        st.success(resultado)
                        if nova_situ.lower() == "concluído":
                            if st.button("OK"):
                                st.cache_data.clear()
                                st.rerun()
    else:
        st.success("✔️ Nenhuma emissão pendente de identificação no momento.")

    if botao_voltar():
        st.session_state.view = 'main_menu'
        st.rerun()

def tela_inserir(client):
    render_header("Inserir Nova Emissão")
    st.divider()

    if st.session_state.get("show_success_emissao"):
        st.success("Nova emissão registrada com sucesso")
        if st.button("OK", use_container_width=True, key="ok_sucesso_emissao"):
            del st.session_state["show_success_emissao"]
            st.session_state.view = 'main_menu'
            st.rerun()
        return

    opcoes_identificacao = carregar_opcoes_identificacao(client)
    with st.form("form_nova_emissao", clear_on_submit=False):
        dados = {
            'Dia': st.date_input("Data (DD/MM/AAAA) :red[**\***]"),
            'Fiscal': st.text_input("Fiscal Responsável :red[**\***]"),
            'Local': st.text_input("Local (ou Lat/Lon) :red[**\***]"),
            'Frequência em MHz': st.number_input("Frequência (MHz) :red[**\***]", format="%.3f", step=0.001, min_value=0.0),
            'Largura em kHz': st.number_input("Largura em kHz :red[**\***]", format="%.1f", step=0.1, min_value=0.0),
            'Identificação': st.selectbox(
                "Identificação da Emissão :red[**\***]",
                options=opcoes_identificacao,
                index=None,
                placeholder="Selecione uma opção..."
            ),
            'Responsável pela emissão': st.text_input("Responsável pela Emissão"),
            'Interferente?': st.selectbox(
                "Interferente? :red[**\***]",
                ("Sim", "Não", "Indefinido"),
                index=None,
                placeholder="Selecione uma opção..."
            ),
            'Observações/Detalhes': st.text_area("Observações/Detalhes :red[**\***]")
        }
        submitted = st.form_submit_button("Registrar Emissão", use_container_width=True)

        if submitted:
            erros = []
            if not dados['Fiscal'].strip(): erros.append("Fiscal Responsável")
            if not dados['Local'].strip(): erros.append("Local (ou Lat/Lon)")
            if dados['Frequência em MHz'] is None or dados['Frequência em MHz'] <= 0: erros.append("Frequência (MHz) > 0")
            if dados['Largura em kHz'] is None or dados['Largura em kHz'] <= 0: erros.append("Largura em kHz > 0")
            if dados['Identificação'] is None: erros.append("Identificação da Emissão")
            if dados['Interferente?'] is None: erros.append("Interferente?")
            if not dados['Observações/Detalhes'].strip(): erros.append("Observações/Detalhes")

            if erros:
                st.error("Erro: campos obrigatórios → " + ", ".join(erros))
            else:
                dados['Dia'] = dados['Dia'].strftime('%d/%m/%Y')
                with st.spinner("Registrando..."):
                    if inserir_nova_abordagem(client, dados):
                        st.session_state.show_success_emissao = True
                        st.rerun()
                    else:
                        st.error("Falha ao registrar.")

    if botao_voltar():
        st.session_state.view = 'main_menu'
        st.rerun()

def tela_bsr_erb(client):
    render_header("Inserir BSR / ERB Fake")
    st.divider()

    if 'show_success_popup' in st.session_state:
        st.success(st.session_state.show_success_popup)
        if st.button("OK", use_container_width=True):
            del st.session_state.show_success_popup
            st.session_state.view = 'main_menu'
            st.rerun()
        return

    if 'confirmacao_bsr_erb' in st.session_state:
        st.markdown('<div class="confirm-warning">Confirma que houve mesmo a identificação do equipamento?</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sim, confirmo", use_container_width=True):
                regiao = st.session_state.regiao_bsr_erb
                tipo_ocorrencia = st.session_state.tipo_ocorrencia_bsr_erb
                lat = st.session_state.lat_bsr_erb
                lon = st.session_state.lon_bsr_erb
                with st.spinner("Registrando..."):
                    resultado = registrar_bsr_erb(client, regiao, tipo_ocorrencia, lat, lon)
                del st.session_state.confirmacao_bsr_erb
                del st.session_state.regiao_bsr_erb
                del st.session_state.tipo_ocorrencia_bsr_erb
                del st.session_state.lat_bsr_erb
                del st.session_state.lon_bsr_erb
                if "ERRO" in resultado: 
                    st.error(resultado)
                else: 
                    st.session_state.show_success_popup = resultado
                    st.rerun()
        with col2:
            if st.button("Não, cancelar", use_container_width=True):
                del st.session_state.confirmacao_bsr_erb
                del st.session_state.regiao_bsr_erb
                del st.session_state.tipo_ocorrencia_bsr_erb
                if 'lat_bsr_erb' in st.session_state: del st.session_state.lat_bsr_erb
                if 'lon_bsr_erb' in st.session_state: del st.session_state.lon_bsr_erb
                st.info("Operação cancelada.")
                st.rerun()
    else:
        with st.form("form_bsr_erb"):
            tipo_ocorrencia = st.radio(
                label="Selecione o tipo de ocorrência: :red[**\***]",
                options=('BSR/Jammer', 'ERB Fake'),
                index=None,
                horizontal=True
            )
            regiao = st.text_input("Local/Região da ocorrência: :red[**\***]")
            lat = st.text_input("Latitude (formato: -N.NNNNNN)")
            lon = st.text_input("Longitude (formato: -N.NNNNNN)")
            submitted = st.form_submit_button("Registrar Ocorrência", use_container_width=True)

            if submitted:
                campos_vazios = []
                if tipo_ocorrencia is None:
                    campos_vazios.append("Tipo de ocorrência")
                if not regiao.strip():
                    campos_vazios.append("Local/Região da ocorrência")

                if campos_vazios:
                    st.error(f"Erro: Os seguintes campos são obrigatórios: {', '.join(campos_vazios)}.")
                else:
                    st.session_state.confirmacao_bsr_erb = True
                    st.session_state.regiao_bsr_erb = regiao
                    st.session_state.tipo_ocorrencia_bsr_erb = tipo_ocorrencia
                    st.session_state.lat_bsr_erb = lat
                    st.session_state.lon_bsr_erb = lon
                    st.rerun()

    if botao_voltar(key="voltar_bsr_erb"):
        if 'confirmacao_bsr_erb' in st.session_state: del st.session_state.confirmacao_bsr_erb
        if 'regiao_bsr_erb' in st.session_state: del st.session_state.regiao_bsr_erb
        if 'tipo_ocorrencia_bsr_erb' in st.session_state: del st.session_state.tipo_ocorrencia_bsr_erb
        if 'lat_bsr_erb' in st.session_state: del st.session_state.lat_bsr_erb
        if 'lon_bsr_erb' in st.session_state: del st.session_state.lon_bsr_erb
        st.session_state.view = 'main_menu'
        st.rerun()

# --- LÓGICA PRINCIPAL ---
try:
    client = get_gspread_client()

    if 'view' not in st.session_state:
        st.session_state.view = 'main_menu'

    if st.session_state.view == 'main_menu':
        tela_menu_principal()
    elif st.session_state.view == 'consultar':
        tela_consultar(client)
    elif st.session_state.view == 'inserir':
        tela_inserir(client)
    elif st.session_state.view == 'bsr_erb':
        tela_bsr_erb(client)

except Exception as e:
    st.error("Erro fatal de autenticação ou inicialização. Verifique os seus segredos (secrets.toml).")
    st.exception(e)
