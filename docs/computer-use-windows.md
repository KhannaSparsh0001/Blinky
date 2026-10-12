# Windows computer-use safeguards

## The trap

Microsoft Store can expose multiple windows with the same title: a hidden activation HWND and the visible Store window. Choosing the first title match can send keyboard events to the hidden HWND. A generic label such as `Search` can also match a different app's window if name fallback searches the whole desktop. The Store UI Automation tree may be empty, so a missing Search element must not degrade into a click on another window or the Store window center.

## Routing and execution rules

- Route both `open Microsoft Store and search for Minecraft` and `search Minecraft in Microsoft Store` through `resolve_windows_use_request`.
- Prefer Microsoft's `ms-windows-store://search/?query=...` URI for Store searches; it bypasses unreliable UIA and screen coordinates.
- For explicit app targets, select a supported visible window and do not fall back to another foreground window when no match exists.
- Keep label matching and window-title fallback scoped to the requested app. Refuse ambiguous or missing controls rather than guessing a click.
- Use snapshot-bound UIA element tokens when the tree is available. Use pixels only when grounded in a fresh screenshot with matching coordinate scaling.

## Regression checks

From the repository root, run:

```powershell
pytest common/python/tests/test_cua_targeted_input.py common/python/tests/test_microsoft_store_search.py common/python/tests/test_laya_router.py::TestLayaRouter::test_microsoft_store_search_phrase_resolves_to_fast_windows_use_path
```
