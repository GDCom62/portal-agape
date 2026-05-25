[22:54:41] 🐍 Python dependencies were installed from /mount/src/portal-agape/requirements.txt using uv.

Check if streamlit is installed

Streamlit is already installed

[22:54:42] 📦 Processed dependencies!

2026-05-25 22:54:44.152 Uvicorn server started on 0.0.0.0:8501




2026-05-25 22:55:25.194 Script compilation error

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

  File "/mount/src/portal-agape/app.py", line 265

    else:

         ^

IndentationError: expected an indented block after 'else' statement on line 265

2026-05-25 22:55:25.202 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.

[22:57:37] 🐙 Pulling code changes from Github...

[22:57:38] 📦 Processing dependencies...

[22:57:38] 📦 Processed dependencies!

[22:57:40] 🔄 Updated app!
