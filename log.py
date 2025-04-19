from rich import print
from rich.console import Console
from rich.markdown import Markdown
from configparser import ConfigParser
from typing import Literal, Optional, Dict, Union
from enum import Enum
import time
import os
import inspect

class LogLevelEnum(str, Enum):
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    SUCCESS = 'success'

# 默认日志级别
LogLevel = LogLevelEnum.INFO
# 日志文件路径
LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
# 是否启用文件日志
ENABLE_FILE_LOG = False

def set_log_level(level: Union[str, LogLevelEnum]) -> None:
    """设置日志级别"""
    global LogLevel
    if isinstance(level, str):
        try:
            LogLevel = LogLevelEnum(level.lower())
        except ValueError:
            print(f"[bold red]无效的日志级别: {level}，使用默认级别: {LogLevel}[/bold red]")
    else:
        LogLevel = level

def enable_file_log(enable: bool = True) -> None:
    """启用或禁用文件日志"""
    global ENABLE_FILE_LOG
    ENABLE_FILE_LOG = enable
    if enable and not os.path.exists(LOG_FILE_PATH):
        try:
            os.makedirs(LOG_FILE_PATH)
        except Exception as e:
            print(f"[bold red]创建日志目录失败: {e}[/bold red]")
            ENABLE_FILE_LOG = False

def truncate_path(full_path: str, marker: str = "HeyAuth") -> str:
    """截断路径，只保留从marker开始的部分"""
    try:
        marker_index = full_path.find(marker)
        if marker_index != -1:
            return '.' + full_path[marker_index + len(marker):]
        return full_path
    except Exception:
        return full_path

def get_caller_info(depth: int = 2) -> tuple:
    """获取调用者信息"""
    try:
        frame = inspect.currentframe()
        # 向上查找指定深度的调用帧
        for _ in range(depth):
            if frame.f_back is None:
                break
            frame = frame.f_back
            
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        return truncate_path(filename), lineno
    except Exception:
        return "<unknown>", 0
    finally:
        # 确保引用被释放
        del frame

def log(level: str = 'debug', message: str = ''):
    """
    输出日志
    ---
    通过传入的`level`和`message`参数，输出不同级别的日志信息。<br>
    `level`参数为日志级别，支持`红色error`、`紫色info`、`绿色success`、`黄色warning`、`淡蓝色debug`。<br>
    `message`参数为日志信息。<br>
    """
    level_colors: Dict[str, str] = {
        'debug': '[bold cyan][DEBUG][/bold cyan]',
        'info': '[bold blue][INFO][/bold blue]',
        'warning': '[bold yellow][WARN][/bold yellow]',
        'error': '[bold red][ERROR][/bold red]',
        'success': '[bold green][SUCCESS][/bold green]'
    }
    
    level_value = level.lower()
    lv = level_colors.get(level_value, '[bold magenta][UNKNOWN][/bold magenta]')
    
    # 获取调用者信息
    filename, lineno = get_caller_info(3)  # 考虑lambda调用和包装函数，深度为3
    timestamp = time.strftime('%Y/%m/%d %H:%M:%S %p', time.localtime())
    log_message = f"{lv}\t{timestamp} [bold]From {filename}, line {lineno}[/bold] {message}"
    
    # 根据日志级别判断是否输出
    global LogLevel
    should_log = False
    
    if level_value == 'debug' and LogLevel == LogLevelEnum.DEBUG:
        should_log = True
    elif level_value == 'info' and LogLevel in [LogLevelEnum.DEBUG, LogLevelEnum.INFO]:
        should_log = True
    elif level_value == 'warning' and LogLevel in [LogLevelEnum.DEBUG, LogLevelEnum.INFO, LogLevelEnum.WARNING]:
        should_log = True
    elif level_value == 'error':
        should_log = True
    elif level_value == 'success':
        should_log = False
        
    if should_log:
        print(log_message)
        
        # 文件日志记录
        if ENABLE_FILE_LOG:
            try:
                # 去除rich格式化标记
                clean_message = f"{level_value.upper()}\t{timestamp} From {filename}, line {lineno} {message}"
                log_file = os.path.join(LOG_FILE_PATH, f"{time.strftime('%Y%m%d')}.log")
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{clean_message}\n")
            except Exception as e:
                print(f"[bold red]写入日志文件失败: {e}[/bold red]")

# 便捷日志函数
debug = lambda message: log('debug', message)
info = lambda message: log('info', message)
warning = lambda message: log('warn', message)
error = lambda message: log('error', message)
success = lambda message: log('success', message)

def load_config(config_path: str) -> bool:
    """从配置文件加载日志配置"""
    try:
        if not os.path.exists(config_path):
            return False
            
        config = ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        if 'log' in config:
            log_config = config['log']
            if 'level' in log_config:
                set_log_level(log_config['level'])
            if 'file_log' in log_config:
                enable_file_log(log_config.getboolean('file_log'))
            if 'log_path' in log_config:
                global LOG_FILE_PATH
                custom_path = log_config['log_path']
                if os.path.exists(custom_path) or os.makedirs(custom_path, exist_ok=True):
                    LOG_FILE_PATH = custom_path
        return True
    except Exception as e:
        error(f"加载日志配置失败: {e}")
        return False

def title(title: str = '海枫授权系统 HeyAuth', size: Optional[Literal['h1', 'h2', 'h3', 'h4', 'h5']] = 'h1'):
    """
    输出标题
    ---
    通过传入的`title`参数，输出一个整行的标题。<br>
    `title`参数为标题内容。<br>
    """
    try:
        console = Console()
        markdown_sizes = {
            'h1': '# ',
            'h2': '## ',
            'h3': '### ',
            'h4': '#### ',
            'h5': '##### '
        }
        
        markdown_tag = markdown_sizes.get(size, '# ')
        console.print(Markdown(markdown_tag + title))
    except Exception as e:
        error(f"输出标题失败: {e}")
    finally:
        if 'console' in locals():
            del console