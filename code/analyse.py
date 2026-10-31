"""Analysis for the ИАС: tables in tables/, charts in figures/, key numbers
in results.md. Reads only the tidy CSVs made by build_tables.py.

Blocks: 1 dynamics · 2 commodity structure · 3 geography · 4 RCA ·
5 Grubel–Lloyd · 6 monthly series with events.
All values USD, UN Comtrade, Japan as reporter.
"""
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG, TAB = ROOT / "data", ROOT / "figures", ROOT / "tables"
FIG.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)
BN = 1e9

plt.rcParams.update({
    "font.family": "Arial", "font.size": 12, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 150, "savefig.bbox": "tight",
})

# --- groupings -------------------------------------------------------------
# HS chapters -> commodity groups (Russian labels for the text)
GROUPS = [
    ("Транспортные средства", range(86, 90)),
    ("Машины и оборудование", [84]),
    ("Электрооборудование", [85]),
    ("Оптика, приборы", range(90, 93)),
    ("Химия, пластмассы, каучук", list(range(28, 41))),
    ("Металлы и изделия", range(72, 84)),
    ("Минеральное топливо", [27]),
    ("Руды, минеральное сырьё", range(25, 27)),
    ("Продовольствие", range(1, 25)),
    ("Текстиль, одежда, обувь", range(50, 68)),
]
HS_GROUP = {ch: g for g, chs in GROUPS for ch in chs}


def group_of(hs2):
    return HS_GROUP.get(int(hs2), "Прочее")


EU27 = [40, 56, 100, 191, 196, 203, 208, 233, 246, 251, 276, 300, 348, 372,
        380, 428, 440, 442, 470, 528, 616, 620, 642, 703, 705, 724, 752]
ASEAN = [96, 104, 116, 360, 418, 458, 608, 702, 704, 764]
GULF = [48, 364, 368, 414, 512, 634, 682, 784]
REGIONS = {
    "США": [842], "Китай (с Гонконгом)": [156, 344], "АСЕАН": ASEAN,
    "ЕС-27": EU27, "Респ. Корея": [410], "Тайвань": [490],
    "Персидский залив": GULF, "Австралия": [36], "Россия": [643],
}
REGION = {c: r for r, cs in REGIONS.items() for c in cs}

out = []  # lines for results.md


def note(line=""):
    out.append(line)


def save(fig, name):
    # titles and the source line are written as captions in the Word file
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)


def hhi(shares):
    """Herfindahl–Hirschman index on shares in % (0..10 000)."""
    return float((shares ** 2).sum())


# --- load ----------------------------------------------------------------
ap = pd.read_csv(DATA / "annual_partners.csv")
hs = pd.read_csv(DATA / "annual_hs2.csv", dtype={"hs2": str})
bi = pd.read_csv(DATA / "bilateral_hs2.csv", dtype={"hs2": str})
mo = pd.read_csv(DATA / "monthly.csv")
wo = pd.read_csv(DATA / "world_hs2.csv", dtype={"hs2": str})

# --- 1 dynamics ----------------------------------------------------------
tot = ap[ap.partner_code == 0].pivot(index="year", columns="flow", values="value") / BN
tot["balance"] = tot.X - tot.M
tot["turnover"] = tot.X + tot.M
tot.round(1).to_csv(TAB / "1_dynamics.csv")

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(tot.index, tot.X, label="Экспорт", color="#1f5fa8", lw=2)
ax.plot(tot.index, tot.M, label="Импорт", color="#c0392b", lw=2)
ax.bar(tot.index, tot.balance, label="Сальдо", color="0.6", alpha=0.7)
ax.axhline(0, color="black", lw=0.8)
ax.set_ylabel("млрд долл. США")
ax.legend(frameon=False)
save(fig, "fig1_dynamics")

note("## 1. Динамика")
for y in (2000, 2008, 2011, 2014, 2019, 2022, 2024):
    r = tot.loc[y]
    note(f"- {y}: экспорт {r.X:.0f}, импорт {r.M:.0f}, сальдо {r.balance:+.0f} млрд долл.")
deficit_years = list(tot.index[tot.balance < 0])
note(f"- Годы с дефицитом: {', '.join(map(str, deficit_years))}")
note(f"- Рост экспорта 2000→2024: {tot.X[2024] / tot.X[2000] - 1:+.0%}; "
     f"импорта: {tot.M[2024] / tot.M[2000] - 1:+.0%}")

# --- 2 commodity structure -------------------------------------------------
hs["group"] = hs.hs2.map(group_of)
grp = hs.groupby(["year", "flow", "group"]).value.sum().reset_index()
grp["share"] = grp.value / grp.groupby(["year", "flow"]).value.transform("sum") * 100
shares = grp.pivot_table(index=["flow", "group"], columns="year", values="share")
shares.round(1).to_csv(TAB / "2_commodity_shares.csv")

order = [g for g, _ in GROUPS] + ["Прочее"]
cmap = plt.get_cmap("tab20")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
for ax, flow, title in zip(axes, "XM", ("Экспорт", "Импорт")):
    s = shares.loc[flow].reindex(order).fillna(0)
    ax.stackplot(s.columns, s.values, labels=s.index,
                 colors=[cmap(i) for i in range(len(order))])
    ax.set_title(title, loc="left")
    ax.set_xlim(2000, 2024)
    ax.set_ylim(0, 100)
    ax.grid(False)
axes[0].set_ylabel("% от итога")
# legend under both panels keeps the figure narrow enough to read in Word
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.5, 0.02),
           ncol=3, frameon=False, fontsize=11)
save(fig, "fig2_commodity_structure")

# concentration by HS chapter
hs["share"] = hs.value / hs.groupby(["year", "flow"]).value.transform("sum") * 100
conc = hs.groupby(["year", "flow"]).share.apply(hhi).unstack()
conc.round(0).to_csv(TAB / "2_hhi_commodity.csv")

note("\n## 2. Товарная структура (доля, %)")
for flow, name in (("X", "Экспорт"), ("M", "Импорт")):
    s = shares.loc[flow]
    top = s[2024].sort_values(ascending=False).head(5)
    note(f"- {name} 2024: " + "; ".join(
        f"{g} {v:.1f} (2000: {s.loc[g, 2000]:.1f})" for g, v in top.items()))
note(f"- HHI по главам HS, экспорт: 2000 {conc.loc[2000, 'X']:.0f} → 2024 {conc.loc[2024, 'X']:.0f}; "
     f"импорт: 2000 {conc.loc[2000, 'M']:.0f} → 2024 {conc.loc[2024, 'M']:.0f} (0–10 000)")
fuel = shares.loc[("M", "Минеральное топливо")]
note(f"- Доля топлива в импорте: мин. {fuel.min():.1f} ({fuel.idxmin()}), "
     f"макс. {fuel.max():.1f} ({fuel.idxmax()}), 2024: {fuel[2024]:.1f}")
top_ch = hs[(hs.year == 2024) & (hs.flow == "X")].nlargest(5, "value")
ch99 = hs[(hs.hs2 == "99") & (hs.flow == "X")].set_index("year").share
note(f"- Глава 99 (не классифицировано) в экспорте: 2000 {ch99[2000]:.1f}%, 2024 {ch99[2024]:.1f}% "
     "— входит в «Прочее», нужна сноска")
note("- Топ-5 глав экспорта 2024: " + "; ".join(
    f"{r.hs2} — {r.value / BN:.0f} млрд ({r.share:.1f}%)" for r in top_ch.itertuples()))

# --- 3 geography -----------------------------------------------------------
geo = ap[ap.partner_code != 0].copy()
geo["region"] = geo.partner_code.map(REGION).fillna("Прочие")
reg = geo.groupby(["year", "flow", "region"]).value.sum().reset_index()
world = tot[["X", "M"]].stack().rename("world") * BN
reg = reg.join(world, on=["year", "flow"])
reg["share"] = reg.value / reg.world * 100
rshare = reg.pivot_table(index=["flow", "region"], columns="year", values="share")
rshare.round(1).to_csv(TAB / "3_region_shares.csv")

bal = reg.pivot_table(index=["year", "region"], columns="flow", values="value")
bal = ((bal.X - bal.M) / BN).unstack()
bal.loc[[2000, 2010, 2022, 2024]].T.round(1).to_csv(TAB / "3_region_balance.csv")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
lines = ["США", "Китай (с Гонконгом)", "АСЕАН", "ЕС-27", "Персидский залив"]
colors = ["#1f5fa8", "#c0392b", "#27ae60", "#8e44ad", "#d68910"]
for ax, flow, title in zip(axes, "XM", ("Экспорт", "Импорт")):
    for r, c in zip(lines, colors):
        ax.plot(rshare.columns, rshare.loc[(flow, r)], label=r, color=c, lw=2)
    ax.set_title(title, loc="left")
axes[0].set_ylabel("% от итога")
axes[1].legend(frameon=False, fontsize=10)
save(fig, "fig3_geography")

pshare = geo.assign(share=geo.value / geo.join(world, on=["year", "flow"]).world * 100)
pconc = pshare.groupby(["year", "flow"]).share.apply(hhi).unstack()
pconc.round(0).to_csv(TAB / "3_hhi_partners.csv")

note("\n## 3. География (доля, %)")
for flow, name in (("X", "Экспорт"), ("M", "Импорт")):
    s = rshare.loc[flow]
    note(f"- {name}: " + "; ".join(
        f"{r} {s.loc[r, 2000]:.1f}→{s.loc[r, 2024]:.1f}" for r in lines + ["Россия"]))
us, cn = rshare.loc[("X", "США")], rshare.loc[("X", "Китай (с Гонконгом)")]
overtakes = [y for y in us.index if cn[y] > us[y]]
note(f"- Годы, когда экспорт в Китай+ГК превышал экспорт в США: {', '.join(map(str, overtakes))}")
cx = geo[geo.flow == "X"].pivot(index="year", columns="partner_code", values="value")
note(f"- Только КНР (без ГК) > США: {', '.join(map(str, cx.index[cx[156] > cx[842]]))}; "
     f"2024: США {cx.loc[2024, 842] / BN:.0f}, КНР {cx.loc[2024, 156] / BN:.0f} млрд")
note(f"- Сальдо 2024, млрд долл.: " + "; ".join(
    f"{r} {bal.loc[2024, r]:+.0f}" for r in lines + ["Россия"]))
note(f"- HHI по партнёрам, экспорт: 2000 {pconc.loc[2000, 'X']:.0f} → 2024 {pconc.loc[2024, 'X']:.0f}")

# --- 4 RCA (Balassa) -------------------------------------------------------
note("\n## 4. RCA (Balassa), главы HS")
rca_rows = []
for y in sorted(wo.year.unique()):
    w = wo[wo.year == y].groupby("hs2").value.sum()
    j = hs[(hs.year == y) & (hs.flow == "X")].set_index("hs2").value
    rca = (j / j.sum()) / (w / w.sum())
    rca_rows.append(rca.rename(y))
# ch. 99 = goods not classified elsewhere: an RCA for it means nothing
rca = pd.concat(rca_rows, axis=1).dropna().drop("99", errors="ignore")
top = rca.sort_values(2024, ascending=False).head(12)
note("- RCA>1 в 2024: " + str(int((rca[2024] > 1).sum())) + " глав из " + str(len(rca)))
note("- Топ-12 (2005 → 2024): " + "; ".join(
    f"{h} {r[2005]:.2f}→{r[2024]:.2f}" for h, r in top.iterrows()))

CH_NAMES = {
    "37": "фото- и кинотовары (вкл. фоторезисты)", "87": "автомобили и части",
    "92": "музыкальные инструменты", "72": "чёрные металлы", "74": "медь",
    "89": "суда", "90": "оптика, приборы", "81": "прочие недраг. металлы",
    "38": "прочая химическая продукция", "32": "красители, пигменты",
    "84": "машины, оборудование", "40": "каучук, резина",
    "85": "электрооборудование", "71": "драгоценные металлы",
}
rca.round(2).sort_values(2024, ascending=False).assign(
    name=lambda d: d.index.map(lambda h: CH_NAMES.get(h, ""))).to_csv(TAB / "4_rca.csv")
fig, ax = plt.subplots(figsize=(7.5, 4.5))
t = top.iloc[::-1]
labels = [f"{h} {CH_NAMES.get(h, '')}".strip() for h in t.index]
ax.barh(labels, t[2024], color="#1f5fa8", label="2024")
ax.scatter(t[2005], labels, color="#c0392b", zorder=3, label="2005")
ax.axvline(1, color="black", lw=0.8)
ax.set_xlabel("Индекс RCA (Баласса); >1 — сравнительное преимущество")
ax.set_ylabel("Глава ТН ВЭД / HS")
ax.legend(frameon=False)
save(fig, "fig4_rca")

# --- 5 Grubel–Lloyd ----------------------------------------------------------
note("\n## 5. Внутриотраслевая торговля (Грубел–Ллойд, по главам HS)")
p = bi.pivot_table(index=["year", "partner", "hs2"], columns="flow", values="value",
                   fill_value=0)
p["overlap"] = p[["X", "M"]].min(axis=1) * 2
gl = p.groupby(["year", "partner"])[["overlap", "X", "M"]].sum()
gl = (gl.overlap / (gl.X + gl.M) * 100).unstack("year")
gl = gl.sort_values(2024, ascending=False)
gl.round(1).to_csv(TAB / "5_grubel_lloyd.csv")

PARTNER_RU = {
    "USA": "США", "China": "КНР", "Rep. of Korea": "Респ. Корея",
    "Other Asia, nes": "Тайвань", "China, Hong Kong SAR": "Гонконг (КНР)",
    "Thailand": "Таиланд", "Viet Nam": "Вьетнам", "Malaysia": "Малайзия",
    "Indonesia": "Индонезия", "Philippines": "Филиппины",
    "Singapore": "Сингапур", "India": "Индия", "Germany": "Германия",
    "Australia": "Австралия", "Saudi Arabia": "Саудовская Аравия",
    "United Arab Emirates": "ОАЭ", "World": "Мир",
}
fig, ax = plt.subplots(figsize=(8, 5.5))
t = gl.iloc[::-1]
names = [PARTNER_RU.get(n, n) for n in t.index]
yy = range(len(t))
ax.barh([y + 0.27 for y in yy], t[2005], height=0.27, color="#aec7e8", label="2005")
ax.barh(list(yy), t[2015], height=0.27, color="#6b9bd1", label="2015")
ax.barh([y - 0.27 for y in yy], t[2024], height=0.27, color="#1f5fa8", label="2024")
ax.set_yticks(list(yy), names)
ax.set_xlabel("Индекс Грубела–Ллойда, %")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
save(fig, "fig6_grubel_lloyd")
note("- GL, % (2005 → 2015 → 2024): " + "; ".join(
    f"{n} {r[2005]:.0f}→{r[2015]:.0f}→{r[2024]:.0f}" for n, r in gl.iterrows()))

# --- 6 monthly series with events ------------------------------------------
mo["date"] = pd.to_datetime(mo.period.astype(str), format="%Y%m")
mw = mo[mo.partner_code == 0].pivot(index="date", columns="flow", values="value") / BN
mw.round(2).to_csv(TAB / "6_monthly_world.csv")
mp = mo[mo.flow == "X"].pivot(index="date", columns="partner", values="value") / BN
mp.round(2).to_csv(TAB / "6_monthly_exports_by_partner.csv")

EVENTS = [
    ("2011-03", "Фукусима"), ("2014-04", "НДС 5→8%"),
    ("2018-07", "Тарифы США–КНР"), ("2019-07", "Ограничения\nпротив Кореи"),
    ("2020-04", "COVID-19"), ("2022-01", "RCEP"),
    ("2022-03", "Санкции против\nРФ, энергошок"), ("2023-07", "Экспортный\nконтроль чипов"),
    ("2025-04", "Тарифы США"),
]
fig, ax = plt.subplots(figsize=(10, 5))
roll = mw.rolling(3).mean()
ax.plot(roll.index, roll.X, color="#1f5fa8", lw=1.8, label="Экспорт (скольз. ср. 3 мес.)")
ax.plot(roll.index, roll.M, color="#c0392b", lw=1.8, label="Импорт (скольз. ср. 3 мес.)")
top_y = ax.get_ylim()[1]
for i, (d, label) in enumerate(EVENTS):
    x = pd.Timestamp(d)
    ax.axvline(x, color="0.5", lw=0.8, ls="--")
    ax.text(x, top_y * (1.0 - 0.06 * (i % 3)), label, fontsize=9, ha="left", va="top",
            bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.85))
ax.set_ylabel("млрд долл. США в месяц")
ax.legend(frameon=False, loc="lower right")
save(fig, "fig5_events")

note("\n## 6. Ивент-анализ: изменение за 6 мес. после события vs 6 мес. до (экспорт / импорт)")
ev_rows = []
for d, label in EVENTS:
    x = pd.Timestamp(d)
    before = mw[(mw.index < x) & (mw.index >= x - pd.DateOffset(months=6))].mean()
    after = mw[(mw.index >= x) & (mw.index < x + pd.DateOffset(months=6))].mean()
    ch = after / before - 1
    note(f"- {d} {label.replace(chr(10), ' ')}: экспорт {ch.X:+.1%}, импорт {ch.M:+.1%}")
    ev_rows.append({"date": d, "event": label.replace("\n", " "),
                     "export_change_pct": round(ch.X * 100, 1),
                     "import_change_pct": round(ch.M * 100, 1)})
ev = pd.DataFrame(ev_rows)
ev.to_csv(TAB / "6_events.csv", index=False)
fig, ax = plt.subplots(figsize=(10, 5))
xx = range(len(ev))
ax.bar([x - 0.2 for x in xx], ev.export_change_pct, width=0.4, color="#1f5fa8", label="Экспорт")
ax.bar([x + 0.2 for x in xx], ev.import_change_pct, width=0.4, color="#c0392b", label="Импорт")
ax.set_xticks(list(xx), [f"{textwrap.fill(e, 13)}\n{d}" for d, e in zip(ev.date, ev.event)],
              fontsize=9)
ax.axhline(0, color="black", lw=0.8)
ax.set_ylabel("изменение, %")
ax.legend(frameon=False)
ax.grid(axis="x", visible=False)
save(fig, "fig7_event_changes")
y25 = mw[mw.index.year == 2025].sum()
y24 = mw[mw.index.year == 2024].sum()
note(f"- 2025 (сумма месяцев): экспорт {y25.X:.0f}, импорт {y25.M:.0f} млрд; "
     f"к 2024: {y25.X / y24.X - 1:+.1%} / {y25.M / y24.M - 1:+.1%}")
us_m = mp["USA"]
note(f"- Экспорт в США 2025 к 2024: {us_m[us_m.index.year == 2025].sum() / us_m[us_m.index.year == 2024].sum() - 1:+.1%}")

(ROOT / "results.md").write_text(
    "# Результаты расчётов (генерируется code/analyse.py — не править руками)\n\n"
    "Все стоимости — млрд долл. США, UN Comtrade, отчётность Японии.\n\n"
    + "\n".join(out) + "\n")
print("\n".join(out))
