# S6: glossary + dashboard explainers

Edit `docs/glossary.json` only. Each entry has `term`, `aka`, `category`, `who`, `why`, `how`,
`what`, `example`, `links` (each link verified to load, with a `checked` note) and `related`
(existing terms only).

Write for an early-high-school reader without dumbing down the mechanism.

**Contract:** `tests/test_glossary.py` (schema, unique terms, valid `related`, https links).

**Time box:** 2 h.
