# S7: test hardening

Add tests in `tests/contrib/` for edge cases:
- empty graphs;
- all-NaN proteins;
- k > number of candidates;
- protein groups with isoforms;
- non-ASCII input to every MCP tool.

You may also add type hints to contrib code and tighten the CI workflow (propose `.github/`
changes to Amit; that path is protected).

**Rules:** tests may only be **added**. A test that exposes a core bug is reported to Amit, not
fixed in core by you.

**Time box:** 2 h.
