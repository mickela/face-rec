Run app directly with python, not flask:

```sh
python app.py
```


Activate .venv:
```sh
source /Users/mickela/facerec/.venv/bin/activate
```



Install dependencies:
```sh
pip install -r requirements.txt --prefer-binary --trusted-host pypi.org --trusted-host files.pythonhosted.org
```
If you hit "Preparing metadata (pyproject.toml)" hangs, the `--prefer-binary` flag avoids building from source. If SSL errors occur, the `--trusted-host` flags help.