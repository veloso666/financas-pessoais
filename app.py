import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy import extract
from db import init_db, get_session, Categoria, Transacao, TipoTransacao

st.set_page_config(
    page_title="Financas Pessoais",
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def setup():
    init_db()

setup()


def parse_brl(texto):
    """Converte '2.622,83' ou '2622.83' para Decimal."""
    t = texto.strip().replace("R$", "").strip()
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    return Decimal(t)


def fmt_brl(value):
    try:
        v = float(value)
        return "R$ {:,.2f}".format(v).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def load_transacoes(mes=None, ano=None):
    session = get_session()
    try:
        q = (
            session.query(
                Transacao.id,
                Transacao.data,
                Transacao.descricao,
                Transacao.valor,
                Transacao.tipo,
                Categoria.nome.label("categoria"),
                Categoria.cor.label("cor"),
            )
            .outerjoin(Categoria)
        )
        if mes:
            q = q.filter(extract("month", Transacao.data) == mes)
        if ano:
            q = q.filter(extract("year", Transacao.data) == ano)
        rows = q.order_by(Transacao.data.desc()).all()
        if not rows:
            return pd.DataFrame(columns=["id","data","descricao","valor","tipo","categoria","cor"])
        df = pd.DataFrame(rows, columns=["id","data","descricao","valor","tipo","categoria","cor"])
        df["valor"] = df["valor"].astype(float)
        return df
    finally:
        session.close()


def load_categorias():
    session = get_session()
    try:
        return session.query(Categoria).order_by(Categoria.nome).all()
    finally:
        session.close()


with st.sidebar:
    st.title("Financas")
    st.markdown("---")
    pagina = st.radio(
        "Navegacao",
        ["Dashboard", "Lancar", "Evolucao", "Categorias"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    anos_disponiveis = list(range(2023, date.today().year + 2))
    ano_sel = st.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(date.today().year))
    meses = {
        1:"Janeiro",2:"Fevereiro",3:"Marco",4:"Abril",
        5:"Maio",6:"Junho",7:"Julho",8:"Agosto",
        9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro",
    }
    mes_sel = st.selectbox("Mes", list(meses.keys()), format_func=lambda x: meses[x], index=date.today().month - 1)


st.markdown("""
<style>
.mcard{background:#1e1e2e;border-radius:12px;padding:20px 24px;border-left:4px solid;}
.mcard.verde{border-color:#43A047;} .mcard.vermelho{border-color:#E53935;} .mcard.azul{border-color:#1E88E5;}
.mcard label{font-size:.8rem;color:#aaa;text-transform:uppercase;letter-spacing:1px;}
.mcard .val{font-size:1.8rem;font-weight:700;margin-top:4px;}
.mcard.verde .val{color:#43A047;} .mcard.vermelho .val{color:#E53935;} .mcard.azul .val{color:#1E88E5;}
</style>""", unsafe_allow_html=True)


def metric_card(label, value, tipo):
    st.markdown(f'<div class="mcard {tipo}"><label>{label}</label><div class="val">{value}</div></div>', unsafe_allow_html=True)


if pagina == "Dashboard":
    st.title("Dashboard - " + meses[mes_sel] + " / " + str(ano_sel))
    df = load_transacoes(mes=mes_sel, ano=ano_sel)
    gastos = df[df["tipo"]=="gasto"]["valor"].sum() if not df.empty else 0
    receitas = df[df["tipo"]=="receita"]["valor"].sum() if not df.empty else 0
    saldo = receitas - gastos

    c1,c2,c3 = st.columns(3)
    with c1: metric_card("Receitas", fmt_brl(receitas), "verde")
    with c2: metric_card("Gastos", fmt_brl(gastos), "vermelho")
    with c3: metric_card("Saldo", fmt_brl(saldo), "azul" if saldo >= 0 else "vermelho")
    st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum lancamento encontrado. Use Lancar para adicionar.")
    else:
        cl, cr = st.columns(2)
        with cl:
            st.subheader("Gastos por categoria")
            dg = df[df["tipo"]=="gasto"].copy()
            if not dg.empty:
                pc = dg.groupby(["categoria","cor"])["valor"].sum().reset_index().sort_values("valor", ascending=False)
                fig = px.pie(pc, values="valor", names="categoria", color="categoria",
                             color_discrete_map=dict(zip(pc["categoria"],pc["cor"])), hole=0.45)
                fig.update_traces(textinfo="percent+label", textfont_size=12)
                fig.update_layout(showlegend=False, margin=dict(t=10,b=10,l=10,r=10), height=320)
                st.plotly_chart(fig, use_container_width=True)
        with cr:
            st.subheader("Top gastos")
            dg2 = df[df["tipo"]=="gasto"].copy()
            if not dg2.empty:
                top = dg2.groupby("descricao")["valor"].sum().reset_index().sort_values("valor",ascending=True).tail(10)
                fig2 = px.bar(top, x="valor", y="descricao", orientation="h",
                              color_discrete_sequence=["#E53935"], labels={"valor":"R$","descricao":""})
                fig2.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=320, xaxis_tickformat=",.2f")
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Lancamentos do mes")
        dd = df.copy()
        dd["data"] = pd.to_datetime(dd["data"]).dt.strftime("%d/%m/%Y")
        dd["valor_fmt"] = dd["valor"].apply(fmt_brl)
        dd["tipo_label"] = dd["tipo"].map({"gasto":"Gasto","receita":"Receita"})
        st.dataframe(dd[["data","descricao","categoria","tipo_label","valor_fmt"]].rename(
            columns={"data":"Data","descricao":"Descricao","categoria":"Categoria","tipo_label":"Tipo","valor_fmt":"Valor"}
        ), use_container_width=True, hide_index=True)


elif pagina == "Lancar":
    st.title("Lancar transacao")
    categorias = load_categorias()
    cat_map = {c.nome: c.id for c in categorias}
    cat_nomes = list(cat_map.keys())

    with st.form("form_lancamento", clear_on_submit=True):
        c1,c2 = st.columns(2)
        with c1:
            tipo = st.selectbox("Tipo", ["gasto","receita"], format_func=lambda x: "Gasto" if x=="gasto" else "Receita")
            descricao = st.text_input("Descricao *", placeholder="ex: Aluguel, Nubank...")
            valor_txt = st.text_input("Valor (R$) *", placeholder="ex: 2.622,83")
        with c2:
            data_t = st.date_input("Data *", value=date.today())
            cat_nome = st.selectbox("Categoria", cat_nomes)
        if st.form_submit_button("Salvar lancamento", use_container_width=True, type="primary"):
            erro = None
            if not descricao.strip():
                erro = "Descricao obrigatoria."
            elif not valor_txt.strip():
                erro = "Valor obrigatorio."
            else:
                try:
                    valor_dec = parse_brl(valor_txt)
                    if valor_dec <= 0:
                        erro = "Valor deve ser maior que zero."
                except (InvalidOperation, Exception):
                    erro = "Valor invalido. Use o formato: 2.622,83 ou 2622.83"
            if erro:
                st.error(erro)
            else:
                session = get_session()
                try:
                    session.add(Transacao(data=data_t, descricao=descricao.strip(),
                                         valor=valor_dec, tipo=TipoTransacao(tipo),
                                         categoria_id=cat_map.get(cat_nome)))
                    session.commit()
                    st.success("Lancamento salvo: " + descricao + " - " + fmt_brl(valor_dec))
                except Exception as e:
                    session.rollback(); st.error("Erro ao salvar: " + str(e))
                finally:
                    session.close()

    st.markdown("---")
    st.subheader("Excluir lancamentos")
    df_all = load_transacoes(mes=mes_sel, ano=ano_sel)
    if df_all.empty:
        st.info("Nenhum lancamento no periodo selecionado.")
    else:
        df_all["data_fmt"] = pd.to_datetime(df_all["data"]).dt.strftime("%d/%m/%Y")
        df_all["label"] = df_all.apply(lambda r: r["data_fmt"]+" | "+r["descricao"]+" | "+fmt_brl(r["valor"]), axis=1)
        sel_label = st.selectbox("Selecionar lancamento para excluir", df_all["label"].tolist())
        sel_id = int(df_all[df_all["label"]==sel_label]["id"].values[0])
        if st.button("Excluir selecionado", type="secondary"):
            session = get_session()
            try:
                t = session.query(Transacao).filter(Transacao.id==sel_id).first()
                if t:
                    session.delete(t); session.commit()
                    st.success("Lancamento excluido."); st.rerun()
            except Exception as e:
                session.rollback(); st.error("Erro: "+str(e))
            finally:
                session.close()


elif pagina == "Evolucao":
    st.title("Evolucao - " + str(ano_sel))
    df_ano = load_transacoes(ano=ano_sel)
    if df_ano.empty:
        st.info("Sem dados para o ano selecionado.")
    else:
        df_ano["mes"] = pd.to_datetime(df_ano["data"]).dt.month
        df_ano["mes_nome"] = df_ano["mes"].map(meses)
        resumo = df_ano.groupby(["mes","mes_nome","tipo"])["valor"].sum().reset_index()
        rp = resumo.pivot_table(index=["mes","mes_nome"], columns="tipo", values="valor", fill_value=0).reset_index()
        if "receita" not in rp.columns: rp["receita"] = 0.0
        if "gasto" not in rp.columns: rp["gasto"] = 0.0
        rp = rp.sort_values("mes")
        rp["saldo"] = rp["receita"] - rp["gasto"]

        st.subheader("Receitas vs Gastos por mes")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=rp["mes_nome"], y=rp["receita"], name="Receitas", marker_color="#43A047"))
        fig.add_trace(go.Bar(x=rp["mes_nome"], y=rp["gasto"], name="Gastos", marker_color="#E53935"))
        fig.add_trace(go.Scatter(x=rp["mes_nome"], y=rp["saldo"], name="Saldo", mode="lines+markers",
                                 line=dict(color="#1E88E5",width=3), marker=dict(size=8), yaxis="y2"))
        fig.update_layout(barmode="group", yaxis2=dict(overlaying="y",side="right",showgrid=False),
                          legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
                          margin=dict(t=30,b=10), height=400, yaxis_tickformat=",.2f")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Gastos por categoria ao longo do ano")
        dga = df_ano[df_ano["tipo"]=="gasto"].copy()
        if not dga.empty:
            cm = dga.groupby(["mes","mes_nome","categoria","cor"])["valor"].sum().reset_index().sort_values("mes")
            cores = dict(zip(cm["categoria"], cm["cor"]))
            fig2 = px.bar(cm, x="mes_nome", y="valor", color="categoria", color_discrete_map=cores,
                          labels={"mes_nome":"Mes","valor":"R$","categoria":"Categoria"}, barmode="stack")
            fig2.update_layout(margin=dict(t=10,b=10), height=380, yaxis_tickformat=",.2f",
                               legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Resumo anual")
        tbl = rp[["mes_nome","receita","gasto","saldo"]].copy()
        tbl.columns = ["Mes","Receitas (R$)","Gastos (R$)","Saldo (R$)"]
        for col in ["Receitas (R$)","Gastos (R$)","Saldo (R$)"]:
            tbl[col] = tbl[col].apply(fmt_brl)
        st.dataframe(tbl, use_container_width=True, hide_index=True)


elif pagina == "Categorias":
    st.title("Gerenciar categorias")
    categorias = load_categorias()
    st.subheader("Categorias existentes")
    if categorias:
        cols = st.columns(4)
        for i, cat in enumerate(categorias):
            with cols[i % 4]:
                st.markdown(f'<div style="background:{cat.cor};border-radius:8px;padding:8px 12px;color:#fff;font-weight:600;margin-bottom:8px;">{cat.nome}</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("Nova categoria")
    with st.form("form_categoria", clear_on_submit=True):
        c1,c2 = st.columns([3,1])
        with c1: novo_nome = st.text_input("Nome da categoria")
        with c2: nova_cor = st.color_picker("Cor", "#1E88E5")
        if st.form_submit_button("Adicionar", type="primary"):
            if not novo_nome.strip():
                st.error("Nome obrigatorio.")
            else:
                session = get_session()
                try:
                    session.add(Categoria(nome=novo_nome.strip(), cor=nova_cor))
                    session.commit()
                    st.success("Categoria " + novo_nome + " criada!")
                    st.rerun()
                except Exception as e:
                    session.rollback(); st.error("Erro: "+str(e))
                finally:
                    session.close()