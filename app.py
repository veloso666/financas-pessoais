import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy import extract
from io import BytesIO
from fpdf import FPDF
from db import init_db, get_session, Categoria, Transacao, TipoTransacao, Meta

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
                Transacao.id, Transacao.data, Transacao.descricao,
                Transacao.valor, Transacao.tipo,
                Categoria.nome.label("categoria"),
                Categoria.cor.label("cor"),
            ).outerjoin(Categoria)
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


def load_metas(mes, ano):
    session = get_session()
    try:
        rows = (
            session.query(Meta.id, Meta.limite, Categoria.nome, Categoria.cor)
            .join(Categoria)
            .filter(Meta.mes == mes, Meta.ano == ano)
            .all()
        )
        if not rows:
            return pd.DataFrame(columns=["id","limite","categoria","cor"])
        df = pd.DataFrame(rows, columns=["id","limite","categoria","cor"])
        df["limite"] = df["limite"].astype(float)
        return df
    finally:
        session.close()


def gerar_pdf(mes, ano, meses_map):
    df = load_transacoes(mes=mes, ano=ano)
    gastos = df[df["tipo"]=="gasto"]["valor"].sum() if not df.empty else 0
    receitas = df[df["tipo"]=="receita"]["valor"].sum() if not df.empty else 0
    saldo = receitas - gastos

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_fill_color(30, 30, 46)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "Relatorio Financeiro", new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, meses_map[mes] + " / " + str(ano), new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.ln(6)

    def card(label, valor, r, g, b):
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(58, 10, label, align="C", fill=True)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0 if label == "Saldo" else 5, 10, "", fill=False)
        w = 58
        x = pdf.get_x() - (0 if label == "Saldo" else 5)
        pdf.set_x(x)
        pdf.cell(w, 10, fmt_brl(valor), align="C", fill=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(255,255,255)
    pdf.set_fill_color(67,160,71)
    pdf.cell(58, 10, "Receitas", align="C", fill=True)
    pdf.set_fill_color(229,57,53)
    pdf.cell(5, 10, "", fill=False)
    pdf.cell(58, 10, "Gastos", align="C", fill=True)
    pdf.set_fill_color(30,136,229)
    pdf.cell(5, 10, "", fill=False)
    pdf.cell(0, 10, "Saldo", align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(67,160,71)
    pdf.cell(58, 10, fmt_brl(receitas), align="C", fill=True)
    pdf.set_fill_color(229,57,53)
    pdf.cell(5, 10, "", fill=False)
    pdf.cell(58, 10, fmt_brl(gastos), align="C", fill=True)
    pdf.set_fill_color(30,136,229 if saldo >= 0 else 229,57,53)
    pdf.cell(5, 10, "", fill=False)
    pdf.cell(0, 10, fmt_brl(saldo), align="C", fill=True)
    pdf.ln(10)

    if not df.empty:
        dg = df[df["tipo"]=="gasto"].copy()
        if not dg.empty:
            por_cat = dg.groupby("categoria")["valor"].sum().reset_index().sort_values("valor", ascending=False)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(30,30,46)
            pdf.cell(0, 8, "Gastos por Categoria", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_fill_color(240,240,240)
            pdf.set_text_color(0,0,0)
            pdf.cell(100, 7, "Categoria", border=1, fill=True)
            pdf.cell(0, 7, "Valor", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            fill = False
            for _, row in por_cat.iterrows():
                pdf.set_fill_color(250,250,250) if fill else pdf.set_fill_color(255,255,255)
                pdf.cell(100, 7, str(row["categoria"]), border=1, fill=True)
                pdf.cell(0, 7, fmt_brl(row["valor"]), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
                fill = not fill
            pdf.ln(6)

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30,30,46)
        pdf.cell(0, 8, "Lancamentos do Mes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_fill_color(240,240,240)
        pdf.set_text_color(0,0,0)
        pdf.cell(25, 7, "Data", border=1, fill=True)
        pdf.cell(80, 7, "Descricao", border=1, fill=True)
        pdf.cell(40, 7, "Categoria", border=1, fill=True)
        pdf.cell(25, 7, "Tipo", border=1, fill=True)
        pdf.cell(0, 7, "Valor", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        fill = False
        for _, row in df.iterrows():
            pdf.set_fill_color(250,250,250) if fill else pdf.set_fill_color(255,255,255)
            data_str = pd.to_datetime(row["data"]).strftime("%d/%m/%Y")
            desc = str(row["descricao"])[:35]
            cat = str(row["categoria"] or "")[:18]
            tipo = "Gasto" if row["tipo"] == "gasto" else "Receita"
            pdf.cell(25, 6, data_str, border=1, fill=True)
            pdf.cell(80, 6, desc, border=1, fill=True)
            pdf.cell(40, 6, cat, border=1, fill=True)
            pdf.cell(25, 6, tipo, border=1, fill=True)
            pdf.cell(0, 6, fmt_brl(row["valor"]), border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            fill = not fill

    buf = BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return buf


with st.sidebar:
    st.title("Financas")
    st.markdown("---")
    pagina = st.radio(
        "Nav",
        ["Dashboard", "Lancar", "Metas", "Importar CSV", "Relatorio PDF", "Evolucao", "Categorias"],
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
.mcard.verde{border-color:#43A047;}.mcard.vermelho{border-color:#E53935;}.mcard.azul{border-color:#1E88E5;}
.mcard label{font-size:.8rem;color:#aaa;text-transform:uppercase;letter-spacing:1px;}
.mcard .val{font-size:1.8rem;font-weight:700;margin-top:4px;}
.mcard.verde .val{color:#43A047;}.mcard.vermelho .val{color:#E53935;}.mcard.azul .val{color:#1E88E5;}
.alerta{background:#3d1a1a;border-left:4px solid #E53935;border-radius:8px;padding:10px 16px;margin:6px 0;}
.ok{background:#1a3d1f;border-left:4px solid #43A047;border-radius:8px;padding:10px 16px;margin:6px 0;}
</style>""", unsafe_allow_html=True)


def metric_card(label, value, tipo):
    st.markdown(f'<div class="mcard {tipo}"><label>{label}</label><div class="val">{value}</div></div>', unsafe_allow_html=True)


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
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

    df_metas = load_metas(mes_sel, ano_sel)
    if not df_metas.empty and not df.empty:
        dg = df[df["tipo"]=="gasto"].copy()
        gasto_cat = dg.groupby("categoria")["valor"].sum().reset_index() if not dg.empty else pd.DataFrame(columns=["categoria","valor"])
        alertas = []
        for _, m in df_metas.iterrows():
            gasto = gasto_cat[gasto_cat["categoria"]==m["categoria"]]["valor"].sum() if not gasto_cat.empty else 0
            pct = (gasto / m["limite"] * 100) if m["limite"] > 0 else 0
            alertas.append({"cat": m["categoria"], "limite": m["limite"], "gasto": gasto, "pct": pct})
        alertas_warn = [a for a in alertas if a["pct"] >= 80]
        if alertas_warn:
            st.subheader("Alertas de Meta")
            for a in alertas_warn:
                cor_cls = "alerta" if a["pct"] >= 100 else "ok"
                icone = "ESTOURADO" if a["pct"] >= 100 else "Atencao"
                st.markdown(
                    f'<div class="{cor_cls}"><b>{a["cat"]}</b> [{icone}] &nbsp; '
                    f'{fmt_brl(a["gasto"])} de {fmt_brl(a["limite"])} ({a["pct"]:.0f}%)</div>',
                    unsafe_allow_html=True
                )
            st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum lancamento. Use Lancar para adicionar.")
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
            st.subheader("Meta vs Real por categoria")
            if not df_metas.empty and not df.empty:
                dg2 = df[df["tipo"]=="gasto"].copy()
                gasto_cat2 = dg2.groupby("categoria")["valor"].sum().reset_index() if not dg2.empty else pd.DataFrame(columns=["categoria","valor"])
                rows_bar = []
                for _, m in df_metas.iterrows():
                    gasto = float(gasto_cat2[gasto_cat2["categoria"]==m["categoria"]]["valor"].sum()) if not gasto_cat2.empty else 0.0
                    rows_bar.append({"Categoria": m["categoria"], "Gasto": gasto, "Limite": float(m["limite"])})
                df_bar = pd.DataFrame(rows_bar)
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(name="Gasto", x=df_bar["Categoria"], y=df_bar["Gasto"], marker_color="#E53935"))
                fig_m.add_trace(go.Bar(name="Limite", x=df_bar["Categoria"], y=df_bar["Limite"], marker_color="#43A047", opacity=0.5))
                fig_m.update_layout(barmode="overlay", height=320, margin=dict(t=10,b=10,l=10,r=10), yaxis_tickformat=",.2f")
                st.plotly_chart(fig_m, use_container_width=True)
            else:
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


# ── LANCAR ────────────────────────────────────────────────────────────────────
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
                    erro = "Valor invalido. Use: 2.622,83 ou 2622.83"
            if erro:
                st.error(erro)
            else:
                session = get_session()
                try:
                    session.add(Transacao(data=data_t, descricao=descricao.strip(),
                                         valor=valor_dec, tipo=TipoTransacao(tipo),
                                         categoria_id=cat_map.get(cat_nome)))
                    session.commit()
                    st.success("Salvo: " + descricao + " - " + fmt_brl(valor_dec))
                except Exception as e:
                    session.rollback(); st.error("Erro: " + str(e))
                finally:
                    session.close()

    st.markdown("---")
    st.subheader("Excluir lancamentos")
    df_all = load_transacoes(mes=mes_sel, ano=ano_sel)
    if df_all.empty:
        st.info("Nenhum lancamento no periodo.")
    else:
        df_all["data_fmt"] = pd.to_datetime(df_all["data"]).dt.strftime("%d/%m/%Y")
        df_all["label"] = df_all.apply(lambda r: r["data_fmt"]+" | "+r["descricao"]+" | "+fmt_brl(r["valor"]), axis=1)
        sel_label = st.selectbox("Selecionar para excluir", df_all["label"].tolist())
        sel_id = int(df_all[df_all["label"]==sel_label]["id"].values[0])
        if st.button("Excluir selecionado", type="secondary"):
            session = get_session()
            try:
                t = session.query(Transacao).filter(Transacao.id==sel_id).first()
                if t:
                    session.delete(t); session.commit()
                    st.success("Excluido."); st.rerun()
            except Exception as e:
                session.rollback(); st.error("Erro: "+str(e))
            finally:
                session.close()


# ── METAS ─────────────────────────────────────────────────────────────────────
elif pagina == "Metas":
    st.title("Metas de Gasto - " + meses[mes_sel] + " / " + str(ano_sel))
    st.caption("Defina limites de gasto por categoria. O Dashboard mostra alertas quando voce se aproximar ou ultrapassar.")

    categorias = load_categorias()
    cat_map = {c.nome: c.id for c in categorias}

    df_metas = load_metas(mes_sel, ano_sel)
    if not df_metas.empty:
        st.subheader("Metas definidas")
        df = load_transacoes(mes=mes_sel, ano=ano_sel)
        dg = df[df["tipo"]=="gasto"].copy() if not df.empty else pd.DataFrame(columns=["categoria","valor"])
        gasto_cat = dg.groupby("categoria")["valor"].sum().reset_index() if not dg.empty else pd.DataFrame(columns=["categoria","valor"])

        for _, m in df_metas.iterrows():
            gasto = float(gasto_cat[gasto_cat["categoria"]==m["categoria"]]["valor"].sum()) if not gasto_cat.empty else 0.0
            pct = min(gasto / m["limite"] * 100, 100) if m["limite"] > 0 else 0
            cor = "#E53935" if pct >= 100 else "#FB8C00" if pct >= 80 else "#43A047"
            c1,c2,c3,c4 = st.columns([3,2,2,1])
            with c1:
                st.markdown(f"**{m['categoria']}**")
                st.progress(int(pct)/100)
            with c2: st.metric("Gasto", fmt_brl(gasto))
            with c3: st.metric("Limite", fmt_brl(m["limite"]))
            with c4:
                st.markdown(f"<br>", unsafe_allow_html=True)
                if st.button("X", key="del_meta_"+str(m["id"])):
                    session = get_session()
                    try:
                        meta = session.query(Meta).filter(Meta.id==m["id"]).first()
                        if meta:
                            session.delete(meta); session.commit(); st.rerun()
                    finally:
                        session.close()
        st.markdown("---")

    st.subheader("Adicionar meta")
    cats_sem_meta = [c.nome for c in categorias if c.nome not in (df_metas["categoria"].tolist() if not df_metas.empty else [])]
    if not cats_sem_meta:
        st.info("Todas as categorias ja tem meta definida para este mes.")
    else:
        with st.form("form_meta", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1: cat_meta = st.selectbox("Categoria", cats_sem_meta)
            with c2: limite_txt = st.text_input("Limite (R$)", placeholder="ex: 500,00")
            if st.form_submit_button("Salvar meta", type="primary"):
                try:
                    limite_dec = parse_brl(limite_txt)
                    session = get_session()
                    try:
                        session.add(Meta(
                            categoria_id=cat_map[cat_meta],
                            mes=mes_sel, ano=ano_sel,
                            limite=limite_dec
                        ))
                        session.commit()
                        st.success("Meta salva para " + cat_meta + "!")
                        st.rerun()
                    except Exception as e:
                        session.rollback(); st.error("Erro: "+str(e))
                    finally:
                        session.close()
                except Exception:
                    st.error("Valor invalido. Use: 500,00")


# ── IMPORTAR CSV ──────────────────────────────────────────────────────────────
elif pagina == "Importar CSV":
    st.title("Importar extrato CSV")
    st.markdown("""
O CSV deve ter as colunas (com cabecalho):

| data | descricao | valor | tipo | categoria |
|------|-----------|-------|------|-----------|
| 2026-05-01 | Aluguel | 2622.83 | gasto | Moradia |

- **data**: formato YYYY-MM-DD ou DD/MM/YYYY
- **valor**: numero com ponto ou virgula
- **tipo**: `gasto` ou `receita`
- **categoria**: nome exato de uma categoria existente (opcional)
""")

    arquivo = st.file_uploader("Selecione o arquivo CSV", type=["csv"])
    if arquivo:
        try:
            df_csv = pd.read_csv(arquivo, sep=None, engine="python")
            df_csv.columns = [c.strip().lower() for c in df_csv.columns]
            colunas_req = {"data","descricao","valor","tipo"}
            faltando = colunas_req - set(df_csv.columns)
            if faltando:
                st.error("Colunas faltando: " + ", ".join(faltando))
            else:
                df_csv["data_parsed"] = pd.to_datetime(df_csv["data"], dayfirst=True, errors="coerce")
                invalidas = df_csv["data_parsed"].isna().sum()
                if invalidas > 0:
                    st.warning(str(invalidas) + " linha(s) com data invalida serao ignoradas.")
                df_csv = df_csv.dropna(subset=["data_parsed"])

                def parse_val(v):
                    try:
                        return parse_brl(str(v))
                    except Exception:
                        return None

                df_csv["valor_dec"] = df_csv["valor"].apply(parse_val)
                df_csv = df_csv.dropna(subset=["valor_dec"])

                df_prev = df_csv[["data_parsed","descricao","valor_dec","tipo"]].copy()
                df_prev.columns = ["Data","Descricao","Valor","Tipo"]
                df_prev["Valor"] = df_prev["Valor"].apply(lambda x: fmt_brl(x))
                st.subheader("Preview (" + str(len(df_prev)) + " registros)")
                st.dataframe(df_prev, use_container_width=True, hide_index=True)

                categorias = load_categorias()
                cat_map = {c.nome: c.id for c in categorias}

                if st.button("Importar todos", type="primary"):
                    session = get_session()
                    importados = 0
                    erros = 0
                    try:
                        for _, row in df_csv.iterrows():
                            tipo_val = str(row["tipo"]).strip().lower()
                            if tipo_val not in ("gasto","receita"):
                                erros += 1; continue
                            cat_id = None
                            if "categoria" in df_csv.columns:
                                cat_id = cat_map.get(str(row.get("categoria","")).strip())
                            session.add(Transacao(
                                data=row["data_parsed"].date(),
                                descricao=str(row["descricao"]).strip(),
                                valor=row["valor_dec"],
                                tipo=TipoTransacao(tipo_val),
                                categoria_id=cat_id
                            ))
                            importados += 1
                        session.commit()
                        st.success(str(importados) + " lancamentos importados com sucesso!")
                        if erros > 0:
                            st.warning(str(erros) + " linhas ignoradas (tipo invalido).")
                    except Exception as e:
                        session.rollback(); st.error("Erro na importacao: "+str(e))
                    finally:
                        session.close()
        except Exception as e:
            st.error("Erro ao ler CSV: " + str(e))


# ── RELATORIO PDF ─────────────────────────────────────────────────────────────
elif pagina == "Relatorio PDF":
    st.title("Relatorio PDF")
    st.write("Gera um relatorio completo do mes selecionado com resumo, gastos por categoria e todos os lancamentos.")

    df_prev = load_transacoes(mes=mes_sel, ano=ano_sel)
    gastos = df_prev[df_prev["tipo"]=="gasto"]["valor"].sum() if not df_prev.empty else 0
    receitas = df_prev[df_prev["tipo"]=="receita"]["valor"].sum() if not df_prev.empty else 0

    c1,c2,c3 = st.columns(3)
    with c1: metric_card("Receitas", fmt_brl(receitas), "verde")
    with c2: metric_card("Gastos", fmt_brl(gastos), "vermelho")
    with c3: metric_card("Lancamentos", str(len(df_prev)), "azul")
    st.markdown("<br>", unsafe_allow_html=True)

    nome_arquivo = "relatorio_" + meses[mes_sel].lower() + "_" + str(ano_sel) + ".pdf"
    if st.button("Gerar e baixar PDF", type="primary", use_container_width=True):
        with st.spinner("Gerando PDF..."):
            buf = gerar_pdf(mes_sel, ano_sel, meses)
        st.download_button(
            label="Clique aqui para baixar o PDF",
            data=buf,
            file_name=nome_arquivo,
            mime="application/pdf",
            use_container_width=True,
        )


# ── EVOLUCAO ──────────────────────────────────────────────────────────────────
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


# ── CATEGORIAS ────────────────────────────────────────────────────────────────
elif pagina == "Categorias":
    st.title("Gerenciar categorias")
    categorias = load_categorias()
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