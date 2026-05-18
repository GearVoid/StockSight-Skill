# StockSight Visual Specs

Use this reference when exact report formatting matters. Keep generated reports compact, scannable, and consistent.

## Report Order

Every report uses this order:

1. H1 report title
2. One-line summary blockquote
3. Core data section
4. Optional detailed analysis section
5. Risk section
6. Optional action suggestions
7. Optional related news
8. Data source line

## Emoji Semantics

| Symbol | Meaning |
|------|------|
| 📰 | report title or summary |
| 📋 | list/table section |
| 🔍 | detailed analysis |
| ⚠️ | risk section |
| 🎯 | conclusion or action suggestions |
| 🗞️ | related news |
| 📡 | data source |
| 🕐 | timestamp |
| 📈 / 📉 / ➡️ | up / down / flat |
| 💰 | price |
| 📊 | volume or amount |
| 📐 | change percent |
| ⚡ | volume ratio |
| 🔄 | turnover rate |
| 🔥 | anomaly signal |
| 🔸 / 🔶 / 🔴 | watch / warning / danger |
| 🟢 / 🟡 / 🔴 | positive / hold or watch / avoid |

## Table Rules

- Keep tables at 3 to 5 columns.
- Standard anomaly tables may use 5 columns: `股票 | 现价 | 涨跌幅 | 量比 | 异动信号`.
- Standard risk tables may use 4 columns: `股票 | 风险类型 | 偏离说明 | 等级`.
- Use `—` for unavailable values instead of dropping a row.
- Put key identity columns on the left and numeric metrics to the right.

## Number Formatting

| Metric | Format |
|------|------|
| A-share price | `RMB x.xx` |
| Hong Kong price | `HKD x.xx` |
| US price | `USD x.xxxx` |
| Change percent | signed percent plus trend emoji, such as `+3.2% 📈` |
| Volume ratio | two decimals, or `—` when unavailable |
| Turnover rate | one decimal percent |
| Amount | integer in ten-thousand units, with currency prefix when known |

## Cross-Market Rules

| Market | Code | Tag | Currency |
|------|------|------|------|
| Shanghai A-share | `sh` | `[A]` | RMB |
| Shenzhen A-share | `sz` | `[A]` | RMB |
| Hong Kong | `hk` | `[H]` | HKD |
| US | `us` | `[U]` | USD |

Place market tags after the stock name with a space: `600570 恒生电子 [A]`.

When a report mixes markets, sort rows as A-share, Hong Kong, then US. Hong Kong and US rows usually have no volume ratio or turnover rate; show `—` and skip unavailable detection dimensions.

## News Section

Render news only when `ReportData.news` is non-empty.

Standard reports:

```markdown
## 🗞️ 相关资讯

| 来源 | 标题 | 时间 |
|:---|:---|:---|
| 新浪财经 | 恒生电子成交活跃 | 05-18 10:00 |
```

Detailed reports:

```markdown
## 🗞️ 相关资讯

[新浪财经] 恒生电子成交活跃（05-18 10:00）
  盘中成交显著放大，资金关注度提升
```

## Failure Handling

- Missing news API key: skip news.
- News provider error: skip news and keep the core report.
- Empty news results: skip news.
- Missing market metric: show `—`.
- No usable quote data: return a short unavailable-data message.

## Disclaimer

Operation suggestions, target prices, and stop-loss values are technical references only and do not constitute investment advice.
