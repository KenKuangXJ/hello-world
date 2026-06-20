import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import altair as alt
import pandas as pd
import streamlit as st
from datetime import date
from finance.database import (
    init_db, add_expense, list_expenses, stats_by_category,
    daily_stats, delete_expense, get_all_categories, get_months_range,
)
from finance.models import Expense

st.set_page_config(page_title="记账工具", page_icon="💰", layout="centered")

init_db()

CATEGORIES = ["餐饮", "购物", "交通", "住房", "娱乐", "医疗", "教育", "其他"]

if "page" not in st.session_state:
    st.session_state.page = "添加账目"


def page_add():
    st.subheader("📝 添加账目")
    with st.form("add_form", clear_on_submit=True):
        cols = st.columns(2)
        amount = cols[0].number_input("金额", min_value=0.01, step=0.01, format="%.2f")
        category = cols[1].selectbox("分类", CATEGORIES)
        date_val = st.date_input("日期", value=date.today())
        notes = st.text_area("备注", placeholder="可选填写备注...")
        submitted = st.form_submit_button("添加", type="primary", use_container_width=True)
        if submitted and amount > 0:
            exp = Expense(id=None, amount=amount, category=category, date=date_val, notes=notes)
            eid = add_expense(exp)
            st.success(f"✅ 已添加 (ID: {eid})")


def page_list():
    st.subheader("📋 查看账目")
    months = get_months_range()
    categories = get_all_categories()
    today = date.today()

    year = today.year
    month = today.month
    sel_cat = None

    cols = st.columns(3)
    if months:
        opts = [f"{y}-{m:02d}" for y, m in months]
        sel = cols[0].selectbox("月份", opts, index=0)
        year, month = int(sel.split("-")[0]), int(sel.split("-")[1])
    else:
        cols[0].selectbox("月份", ["暂无数据"], disabled=True)

    if categories:
        cat_opts = ["全部"] + categories
        sel_cat = cols[1].selectbox("分类", cat_opts)
        sel_cat = None if sel_cat == "全部" else sel_cat
    else:
        cols[1].selectbox("分类", ["暂无"], disabled=True)

    expenses = list_expenses(year=year, month=month, category=sel_cat)
    if expenses:
        total = sum(e.amount for e in expenses)
        st.caption(f"共 {len(expenses)} 条，合计 ¥{total:.2f}")
        rows = []
        for e in expenses:
            rows.append({
                "ID": e.id, "金额": f"¥{e.amount:.2f}", "分类": e.category,
                "日期": e.date.isoformat(), "备注": e.notes or "-",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("该月份暂无记录")


def page_stats():
    st.subheader("📊 分类统计")
    months = get_months_range()
    today = date.today()

    year = today.year
    month = today.month

    if months:
        opts = [f"{y}-{m:02d}" for y, m in months] + ["全部"]
        sel = st.selectbox("月份", opts, index=0)
        if sel == "全部":
            year, month = None, None
        else:
            year, month = int(sel.split("-")[0]), int(sel.split("-")[1])

    stats = stats_by_category(year=year, month=month)
    if stats:
        st.subheader("柱状图")
        df = pd.DataFrame(stats)
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("category:N", title="分类", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("total:Q", title="金额", axis=alt.Axis(titleAngle=0)),
            tooltip=["category", "total"],
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

        st.subheader("统计表")
        rows = []
        grand_total = 0
        for s in stats:
            rows.append({"分类": s["category"], "笔数": s["count"], "合计": f"¥{s['total']:.2f}"})
            grand_total += s["total"]
        rows.append({"分类": "**合计**", "笔数": sum(s["count"] for s in stats), "合计": f"¥{grand_total:.2f}"})
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("暂无统计数据")

    # 按日期统计（仅当选中具体月份时显示）
    if year and month:
        days = daily_stats(year, month)
        if days:
            st.subheader("📅 按日期统计")
            df_days = pd.DataFrame(days)
            chart = alt.Chart(df_days).mark_bar().encode(
                x=alt.X("date:N", title="日期", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("total:Q", title="金额", axis=alt.Axis(titleAngle=0)),
                tooltip=["date", "total"],
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)


def page_delete():
    st.subheader("🗑️ 删除记录")

    # 月份筛选
    months = get_months_range()
    today = date.today()
    year, month = today.year, today.month
    if months:
        opts = [f"全部"] + [f"{y}-{m:02d}" for y, m in months]
        sel = st.selectbox("筛选月份", opts, index=0)
        if sel == "全部":
            year, month = None, None
        else:
            year, month = int(sel.split("-")[0]), int(sel.split("-")[1])

    expenses = list_expenses(year=year, month=month)
    if not expenses:
        st.info("暂无记录")
        return

    st.caption(f"共 {len(expenses)} 条记录，勾选后点击下方删除按钮")

    # 用 st.data_editor 加勾选框
    rows = []
    for e in expenses:
        rows.append({
            "勾选": False,
            "ID": e.id,
            "金额": f"¥{e.amount:.2f}",
            "分类": e.category,
            "日期": e.date.isoformat(),
            "备注": e.notes or "-",
        })

    edited = st.data_editor(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "勾选": st.column_config.CheckboxColumn("勾选", default=False),
            "ID": "ID",
            "金额": "金额",
            "分类": "分类",
            "日期": "日期",
            "备注": "备注",
        },
        disabled=["ID", "金额", "分类", "日期", "备注"],
    )

    selected = [r["ID"] for r in edited if r["勾选"]]
    if st.button(f"删除选中记录 ({len(selected)} 条)", type="primary", disabled=not selected):
        for eid in selected:
            delete_expense(eid)
        st.success(f"✅ 已删除 {len(selected)} 条记录")
        st.rerun()


pages = {
    "添加账目": page_add,
    "查看账目": page_list,
    "分类统计": page_stats,
    "删除记录": page_delete,
}

st.sidebar.title("💰 记账工具")
for p in pages:
    if st.sidebar.button(p, use_container_width=True, key=f"nav_{p}"):
        st.session_state.page = p

pages[st.session_state.page]()
