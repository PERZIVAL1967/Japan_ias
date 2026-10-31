"""Build the supporting Excel workbook from tables/*.csv (made by analyse.py).

One sheet per analysis block: its data plus the same figure that goes into
the text (figures/*.png from analyse.py), so the workbook and the справка
look identical. Native Excel charts were tried first and looked worse.
Output: Приложение_Япония_торговля.xlsx in the project folder.
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "tables"
FIG = ROOT / "figures"
OUT = ROOT / "Приложение_Япония_торговля.xlsx"
SOURCE = ("Источник: составлено автором по данным UN Comtrade Database "
          "(https://comtradeplus.un.org/, дата обращения: 30.10.2026).")

PARTNER_RU = {
    "USA": "США", "China": "КНР", "Rep. of Korea": "Респ. Корея",
    "Other Asia, nes": "Тайвань", "China, Hong Kong SAR": "Гонконг (КНР)",
    "Thailand": "Таиланд", "Viet Nam": "Вьетнам", "Malaysia": "Малайзия",
    "Indonesia": "Индонезия", "Philippines": "Филиппины",
    "Singapore": "Сингапур", "India": "Индия", "Germany": "Германия",
    "Australia": "Австралия", "Saudi Arabia": "Саудовская Аравия",
    "United Arab Emirates": "ОАЭ", "World": "Мир",
}
HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="1F5FA8")

wb = Workbook()


def sheet(title, df, note, widths=None):
    """Write df with a title row, a note row and a styled header."""
    ws = wb.create_sheet(title)
    ws["A1"] = note
    ws["A1"].font = Font(bold=True, size=12)
    ws["A2"] = SOURCE
    ws["A2"].font = Font(italic=True, size=9, color="666666")
    header_row = 4
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(header_row, j, str(col))
        c.font, c.fill = HEAD, FILL
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    for i, row in enumerate(df.itertuples(index=False), header_row + 1):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, None if pd.isna(v) else v)
    for j in range(1, len(df.columns) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(j, 13)
    ws.freeze_panes = ws.cell(header_row + 1, 2)
    return ws


def figure(ws, df, name, width_px=760):
    """Embed figures/<name>.png to the right of the table, scaled to width_px."""
    img = Image(FIG / f"{name}.png")
    img.height = int(img.height * width_px / img.width)
    img.width = width_px
    ws.add_image(img, f"{get_column_letter(len(df.columns) + 2)}4")


# --- 0 description ------------------------------------------------------------
ws = wb.active
ws.title = "Описание"
lines = [
    ("Товарная структура и географическое распределение внешней торговли Японии", True),
    ("Приложение к информационно-аналитической справке: данные и расчёты", False),
    ("", False),
    (SOURCE, False),
    ("Все стоимостные показатели — млрд долл. США, по отчётности Японии (reporter = Japan).", False),
    ("Расчёты воспроизводимы: code/fetch_comtrade.py → build_tables.py → analyse.py → export_excel.py.", False),
    ("", False),
    ("Листы", True),
    ("1 Динамика — экспорт, импорт, сальдо, оборот, 2000–2024", False),
    ("2 Структура экспорта / 2 Структура импорта — доли товарных групп, %", False),
    ("2 Концентрация — индекс Херфиндаля–Хиршмана по главам ТН ВЭД (0–10 000)", False),
    ("3 География экспорта / 3 География импорта — доли регионов, %", False),
    ("3 Сальдо по регионам — млрд долл.; 3 Концентрация партнёров — ИХХ", False),
    ("4 RCA — индекс выявленных сравнительных преимуществ Балассы по главам ТН ВЭД", False),
    ("5 Грубел–Ллойд — индекс внутриотраслевой торговли с ключевыми партнёрами, %", False),
    ("6 Помесячно — экспорт и импорт, 2010–2025; 6 События — ивент-анализ", False),
    ("", False),
    ("Методические оговорки", True),
    ("• Тайвань в UN Comtrade обозначен как «Other Asia, nes» (код 490).", False),
    ("• ЕС-27 — в постоянном составе за весь период; Китай включает Гонконг, где указано.", False),
    ("• Глава 99 (товары, не классифицированные в других главах) входит в «Прочее» и исключена из RCA.", False),
    ("• RCA 2024: мировой экспорт по 148 отчитавшимся странам (2005 — 172).", False),
    ("• Долларовые ряды отражают и курс иены: падение 2015–2016 и 2022–2024 гг. частично валютное.", False),
    ("• Ивент-анализ: среднее за 6 мес. после события к 6 мес. до; сезонность и курс не очищены.", False),
    ("• Годовые данные за 2025 г. не опубликованы; 2025 г. — сумма месячных данных.", False),
]
for i, (text, bold) in enumerate(lines, 1):
    ws.cell(i, 1, text).font = Font(bold=bold, size=13 if i == 1 else 11)
ws.column_dimensions["A"].width = 110

# --- 1 dynamics ---------------------------------------------------------------
d = pd.read_csv(TAB / "1_dynamics.csv")[["year", "X", "M", "balance", "turnover"]]
d.columns = ["Год", "Экспорт", "Импорт", "Сальдо", "Оборот"]
ws = sheet("1 Динамика", d, "Таблица 1. Внешняя торговля Японии, млрд долл. США")
figure(ws, d, "fig1_dynamics")

# --- 2 structure --------------------------------------------------------------
cs = pd.read_csv(TAB / "2_commodity_shares.csv")
for flow, name in (("X", "экспорта"), ("M", "импорта")):
    t = cs[cs.flow == flow].drop(columns="flow").set_index("group").T.fillna(0)
    t = t[t.loc["2024"].sort_values(ascending=False).index]
    if "Прочее" in t:
        t = t[[c for c in t if c != "Прочее"] + ["Прочее"]]
    t.index = t.index.astype(int)
    t = t.reset_index().rename(columns={"index": "Год"})
    ws = sheet(f"2 Структура {name}", t,
                   f"Товарная структура {name} Японии, % от итога", {1: 8})
    figure(ws, t, "fig2_commodity_structure", width_px=900)

h = pd.read_csv(TAB / "2_hhi_commodity.csv")[["year", "X", "M"]]
h.columns = ["Год", "ИХХ экспорта", "ИХХ импорта"]
ws = sheet("2 Концентрация", h, "Индекс Херфиндаля–Хиршмана по главам ТН ВЭД (0–10 000)")

# --- 3 geography --------------------------------------------------------------
rs = pd.read_csv(TAB / "3_region_shares.csv")
main = ["США", "Китай (с Гонконгом)", "АСЕАН", "ЕС-27", "Персидский залив"]
for flow, name in (("X", "экспорта"), ("M", "импорта")):
    t = rs[rs.flow == flow].drop(columns="flow").set_index("region").T
    rest = [c for c in t if c not in main]
    t = t[main + rest]
    t.index = t.index.astype(int)
    t = t.reset_index().rename(columns={"index": "Год"})
    ws = sheet(f"3 География {name}", t,
                   f"Географическое распределение {name} Японии, % от итога", {1: 8})
    figure(ws, t, "fig3_geography", width_px=900)

b = pd.read_csv(TAB / "3_region_balance.csv").rename(columns={"region": "Регион"})
ws = sheet("3 Сальдо по регионам", b, "Сальдо торговли Японии по регионам, млрд долл. США", {1: 22})

pc = pd.read_csv(TAB / "3_hhi_partners.csv")[["year", "X", "M"]]
pc.columns = ["Год", "ИХХ экспорта", "ИХХ импорта"]
ws = sheet("3 Концентрация партнёров", pc, "Индекс Херфиндаля–Хиршмана по странам-партнёрам")

# --- 4 RCA --------------------------------------------------------------------
r = pd.read_csv(TAB / "4_rca.csv", dtype={"hs2": str})
r = r[["hs2", "name", "2005", "2024"]]
r.columns = ["Глава ТН ВЭД", "Наименование", "RCA 2005", "RCA 2024"]
ws = sheet("4 RCA", r, "Индекс выявленных сравнительных преимуществ (Баласса), RCA > 1 — преимущество",
               {2: 38})
figure(ws, r, "fig4_rca")

# --- 5 Grubel–Lloyd -----------------------------------------------------------
g = pd.read_csv(TAB / "5_grubel_lloyd.csv")
g["partner"] = g.partner.map(PARTNER_RU).fillna(g.partner)
g.columns = ["Партнёр", "2005", "2015", "2024"]
ws = sheet("5 Грубел–Ллойд", g, "Индекс внутриотраслевой торговли Грубела–Ллойда, % (по главам ТН ВЭД)",
               {1: 20})
figure(ws, g, "fig6_grubel_lloyd")

# --- 6 monthly + events -------------------------------------------------------
m = pd.read_csv(TAB / "6_monthly_world.csv")
mp = pd.read_csv(TAB / "6_monthly_exports_by_partner.csv")
m = m.merge(mp.drop(columns="World"), on="date")
m["date"] = pd.to_datetime(m.date).dt.strftime("%Y-%m")
m = m.rename(columns={"date": "Месяц", "X": "Экспорт", "M": "Импорт"})
m["Экспорт, скольз. 3 мес."] = m["Экспорт"].rolling(3).mean().round(2)
m["Импорт, скольз. 3 мес."] = m["Импорт"].rolling(3).mean().round(2)
m = m.rename(columns={k: f"Экспорт: {v}" for k, v in PARTNER_RU.items()})
lead = ["Месяц", "Экспорт", "Импорт", "Экспорт, скольз. 3 мес.", "Импорт, скольз. 3 мес."]
m = m[lead + [c for c in m if c not in lead]]
ws = sheet("6 Помесячно", m, "Помесячная торговля Японии, млрд долл. США", {1: 10})
figure(ws, m, "fig5_events", width_px=900)

e = pd.read_csv(TAB / "6_events.csv")
e.columns = ["Дата", "Событие", "Экспорт, изм. %", "Импорт, изм. %"]
ws = sheet("6 События", e, "Ивент-анализ: среднее за 6 мес. после события к 6 мес. до, %", {2: 30})
figure(ws, e, "fig7_event_changes")

wb.save(OUT)
print(f"saved {OUT.name}: {len(wb.sheetnames)} sheets")
