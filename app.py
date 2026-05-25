IndentationError: expected an indented block after 'if' statement on line 266

2026-05-25 23:51:15.694 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.

[23:51:15] 📦 Processing dependencies...

[23:51:15] 📦 Processed dependencies!

[23:51:17] 🔄 Updated app!

2026-05-25 23:52:16.805 Script compilation error

Traceback (most recent call last):

  File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 591, in _run_script

    code = self._script_cache.get_bytecode(script_path)

  File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/script_cache.py", line 72, in get_bytecode

    filebody = magic.add_magic(filebody, script_path)

  File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/scriptrunner/magic.py", line 45, in add_magic

    tree = ast.parse(code, script_path, "exec")

  File "/usr/local/lib/python3.14/ast.py", line 46, in parse

    return compile(source, filename, mode, flags,

                   _feature_version=feature_version, optimize=optimize)

  File "/mount/src/portal-agape/app.py", line 266

    if st.session_state.autenticado:

                                    ^

IndentationError: expected an indented block after 'if' statement on line 266

2026-05-25 23:52:16.808 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
