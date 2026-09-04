# Prompt templates

`prompt_builder.py` loads these at runtime. Edit the text freely; keep the
`{{placeholder}}` tokens intact (double curly braces, exact spelling).

| File | Placeholders |
|------|--------------|
| `system-selective.txt` | `{{forbidden_tags}}` `{{forbidden_attrs}}` `{{allowed_nodes}}` `{{allowed_attributes}}` `{{theme}}` `{{layout_pattern}}` `{{examples}}` `{{notes}}` |
| `user-selective.txt` | `{{objective}}` `{{components}}` `{{request}}` `{{supplied_content}}` |
| `repair-user.txt` | `{{previous_user}}` `{{problems}}` (retry: previous user message + the list of compiler / pre-validator problems to fix) |

Notes:
- The values come from the `GenerationContract` and the `SlideIR`. Nothing else
  is substituted.
- An unknown `{{token}}` left in a file is reported as an error, not silently
  passed to the model.
- `{{supplied_content}}` expands to an empty string when the request has no
  supplied content, otherwise to a `SUPPLIED CONTENT:` block.
- A `{{placeholder}}` whose value is empty expands to `(none)`.
