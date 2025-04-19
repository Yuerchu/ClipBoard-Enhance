from rich import print; import time, inspect
def log(level, message): print(f"{level} {time.strftime('%H:%M:%S', time.localtime())} [bold]From {inspect.currentframe().f_back.f_back.f_code.co_filename}, line {inspect.currentframe().f_back.f_back.f_lineno}[/bold] {message}")
error = lambda message: log('[bold red][ERROR][/bold red]', message)
info = lambda message: log('[bold blue][INFO][/bold blue]', message)
warning = lambda message: log('[bold yellow][WARN][/bold yellow]', message)
debug = lambda message: log('[bold cyan][DEBUG][/bold cyan]', message)