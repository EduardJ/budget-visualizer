# The checks

The page does not only show the budget, it audits it: every relation the document prints (a total and its lines, the
same figure in two tables, a percentage in the text and the table it comes from) is recomputed and compared.

## Exact, with no tolerance

`pipeline/exact.py` does decimal arithmetic on the **printed tokens**, not on floats. The number of decimals is inferred
from how a token is printed (`2,757.7` has one), so the rounding each figure carries is known exactly.

- `relation(lhs, rhs)`: `lhs` should equal the signed sum of `rhs`. Returns the exact difference and a class.
- `rounds_to(value, printed)`: the same figure printed in euros and in € million: the euro figure must round to
  exactly the printed digits.
- `interval(f, terms)`: the range a derived figure (a percentage, a growth rate) can take when every input varies within
  its own rounding; used for claims in the narrative text.

A check **passes only when the printed figures agree exactly**. A failing check is classed as:

| class | when | shown as |
|---|---|---|
| `rounding` | the gap is within half a unit of the last printed digit of every figure involved, summed | *vetëm rrumbullakim / rounding only* |
| `error` | the gap is larger than that, or two prints of the same figure differ at all | *gabim aritmetik / arithmetic error* |

Both are shown, never hidden, merged or softened. `bound` on each check is that rounding allowance, so anyone can see why
a failure got its class.

## What is checked (kosovo-2026)

561 checks: 407 pass exactly, 95 differ by rounding only, 59 are arithmetic errors. 993 findings: the 977 individual
rows behind failing checks (29 error, 948 rounding) and 16 ambiguities, naming notes and notes.
A `refs` check confirms every node and flow has a source reference (0 without).

Coverage: Tables 1 and 1.1, every relation in every year 2023–2028, stock-flow identities, % of GDP lines; Table 1 ↔ 1.1
duplicates; Table 2 ↔ Table 1; the p.701 tables and their narrative growth claims; about 45 numeric claims in the
narrative (pp.695–702); tables on pp.700, 706, 712; the risk statement tables pp.715–725; the law articles (amounts and
codes cited); every row of Tables 3.1/4.1 (categories, funding sources, children; 2026, 2027, 2028); every column of
Annex 1; the municipal summary pp.211–213; p.210 every year; Table 4.3 every municipality × subtotal × year; every
subtotal row of the project tables (8 columns); project column arithmetic.

## Where the code is

- `datasets/kosovo-2026/adapter/normalize_part2.py`: the first checks (Table 2, central/municipal trees).
- `normalize_part4.py`: the exhaustive ones, built with three helpers:
  - `X(id, group, title_en, title_sq, lhs, rhs, pages, refs)`: a sum relation between printed `Term`s;
  - `RT(...)`: a euro figure against its € million print;
  - `CL(...)`: a figure in the text against the same quantity computed from the printed tables.
- `sq_text.py`: Albanian titles and notes for every check and finding; the run stops if one is missing.

## Adding a check

1. Build the terms from printed tokens, not parsed floats: `term_from(raw_line, value)` finds the token in the printed line,
   so its decimals (and so its rounding) are right.
2. Call `X`, `RT` or `CL` (or `check(...)` for a count) with:
   - a stable `id` and a `group` (the table or page it belongs to),
   - an English `title` and an Albanian `title_sq`, and notes in both languages if you add notes,
   - `pages` (every page involved) and `refs` (the ref ids of the rows involved).
3. Let the helper classify the failure. Never pass a tolerance or a class by hand unless the rule above says so
   (two prints of the same figure that differ are always `error`).
4. Add each mismatching row as a finding (`type: 'mismatch'`, with `cls`) so the reconciliation lists it.
5. `make data snippets && npm run check`, then `make verify`.

## Known findings (kosovo-2026)

Do not "fix" the data; these are what the document prints.

- Table 2 omits €12.0M donor-designated grants that Table 1 counts in spending.
- Municipal ceilings (Table 2, p.210) exceed the sum of municipal plans (Tables 4.1/4.1.B, p.671) by €181,296, the
  document's own "Bilanci" (p.213); category totals differ more (capital −€4.10M, reserves +€4.05M).
- p.701 narrative: central growth 10.0% vs 9.7% in its own table; municipal goods 5.6% vs 5.1%; local total 867.7 vs 867.6.
- Debt 22.0% of GDP (pp.700, 702) vs 21.9% in Table 1.1; 16.91% (p.715) vs 16.84%.
- Table 1: 2023 total spending excludes donor grants; net bank balance 2024 breaks the stock-flow identity by €50.7M.
- Law: €5,289,720 (Ministry of Economy, p.9) not traceable in the tables; sub-programme 11301 named differently in law and table.
- Annex 1 vs Table 3.1: 2027 total +€37, 2028 total +€10,006 (Ministry of Environment +€10,000).
- Table 4.3 2025: Pejë "Taksat Komunale" +€798,931 vs its lines (empty building-permit cell), similar in Deçan, Skenderaj, Viti, summary.
- Risk statement: risk-share tables sum to 94–95%; the PPP "operational" total includes a project under construction; p.706 GDP deviation 440 vs 450.
- 687 project subtotal rows off by €1–15 (rounding); one sub-programme on p.461 has no subtotal rows; 41 malformed date ranges in the PDF.
