import sys, ctypes
import time
import pyperclip
import win32clipboard
import win32con
from win11toast import toast, notify
import pystray
from PIL import Image, ImageDraw
import json
import os
import re
import webbrowser
from PyQt5.QtWidgets import QMessageBox
from urllib.parse import urlparse, urlunparse, parse_qs
import winreg
import subprocess
from netdisk_rules import NETDISK_RULES
import log
from pystray._base import Icon
from PyQt5.QtWidgets import QApplication
import threading
import ctypes
import win32api

# 添加线程锁，确保剪贴板操作的线程安全
clipboard_lock = threading.RLock()
# 添加最大重试次数
MAX_CLIPBOARD_RETRY = 3
# 添加重试延迟时间（秒）
CLIPBOARD_RETRY_DELAY = 0.1

# 全局变量：跟踪每个线程的剪贴板打开状态
clipboard_open_by_thread = {}

# 自定义错误类，用于控制流程
class ClipboardError(Exception):
    """剪贴板操作错误"""
    pass

def clean_text_for_netdisk_detection(text):
    """
    清理文本，去除可能的干扰字符，为网盘链接检测做准备
    """
    # 1. 移除所有emoji字符
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    
    # 2. 尝试移除中文字符（因为链接中通常不含中文）
    text = re.sub(r'[\u4e00-\u9fff]', '', text)
    
    # 3. 尝试移除一些常见的干扰符号（保留URL中可能出现的基本符号）
    text = re.sub(r'[@#$%^&*()_+=<>{}\[\]|\\\'",]', '', text)
    
    return text

# 全局变量
is_clearing_clipboard = False
is_setting_clipboard = False  # 新增：标记是否正在设置剪贴板内容
MAX_HISTORY_SIZE = 10   # 历史记录最大条目数
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 默认配置
config = {
    "check_interval": 0.5,
    "max_history_size": 10,
    "show_notifications": True,
    "truncate_length": 100,
    "enable_netdisk_detection": True,  # 启用网盘链接检测
    "copy_pwd_to_clipboard": True      # 新增：打开网盘链接时复制提取码到剪贴板
}

def load_config():
    """加载配置文件"""
    log.debug('加载配置文件...')
    global config, MAX_HISTORY_SIZE
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
        MAX_HISTORY_SIZE = config["max_history_size"]
    except Exception as e:
        log.error(f"加载配置文件时出错: {e}")
    else:
        log.debug('加载完成')
    
    # 确保配置目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    # 保存当前配置作为默认配置
    save_config()

def save_config():
    """保存配置到文件"""
    log.debug('准备保存配置文件...')
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log.error(f"保存配置文件时出错: {e}")

def is_clipboard_open():
    """检查当前线程是否已打开剪贴板
    
    Returns:
        bool: 是否已打开剪贴板
    """
    thread_id = threading.get_ident()
    return clipboard_open_by_thread.get(thread_id, False)

def safe_open_clipboard(max_retries=MAX_CLIPBOARD_RETRY):
    """安全地打开剪贴板，添加重试机制
    
    Args:
        max_retries: 最大重试次数
        
    Returns:
        bool: 是否成功打开剪贴板
    """
    thread_id = threading.get_ident()
    
    # 检查当前线程是否已经打开剪贴板
    if is_clipboard_open():
        return True  # 剪贴板已经被当前线程打开
    
    for i in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            clipboard_open_by_thread[thread_id] = True
            return True
        except Exception as e:
            if i == max_retries - 1:  # 如果是最后一次尝试
                log.debug(f"打开剪贴板失败: {e}")
                return False
            time.sleep(CLIPBOARD_RETRY_DELAY)  # 等待一段时间再重试
    return False

def safe_close_clipboard():
    """安全地关闭剪贴板，只在当前线程已打开剪贴板时进行关闭
    
    Returns:
        bool: 是否成功关闭剪贴板
    """
    thread_id = threading.get_ident()
    
    # 如果当前线程没有打开剪贴板，跳过关闭操作
    if not clipboard_open_by_thread.get(thread_id, False):
        return True
    
    try:
        win32clipboard.CloseClipboard()
        clipboard_open_by_thread[thread_id] = False
        return True
    except Exception as e:
        # 这里使用debug级别，因为这通常不是致命错误
        log.debug(f"关闭剪贴板失败: {e}")
        # 即使关闭失败，也标记为已关闭，避免后续再次尝试关闭
        clipboard_open_by_thread[thread_id] = False
        return False

def clipboard_operation(operation_func):
    """剪贴板操作装饰器，确保安全打开和关闭剪贴板
    
    Args:
        operation_func: 要执行的剪贴板操作函数
        
    Returns:
        包装后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            if not safe_open_clipboard():
                raise ClipboardError("无法打开剪贴板")
            
            # 执行剪贴板操作
            result = operation_func(*args, **kwargs)
            
            # 操作完成后关闭剪贴板
            safe_close_clipboard()
            
            return result
        except Exception as e:
            # 确保出错时也关闭剪贴板
            safe_close_clipboard()
            raise e
    
    return wrapper

def clear_clipboard(args=None):
    """清空剪贴板内容"""
    log.debug('准备清空剪贴板...')
    global is_clearing_clipboard, previous_content
    
    with clipboard_lock:  # 使用锁确保线程安全
        try:
            is_clearing_clipboard = True
            
            # 使用pyperclip尝试清空剪贴板，它有内置的错误处理
            try:
                pyperclip.copy('')
                # 更新之前的内容为空剪贴板状态
                previous_content = get_clipboard_content()
                return True
            except:
                # 如果pyperclip方法失败，尝试使用win32clipboard
                try:
                    if not safe_open_clipboard():
                        log.error("无法打开剪贴板进行清空操作")
                        return False
                    
                    win32clipboard.EmptyClipboard()
                    safe_close_clipboard()
                    
                    # 更新之前的内容为空剪贴板状态
                    previous_content = get_clipboard_content()
                    return True
                except Exception as e:
                    log.error(f'使用win32clipboard清空剪贴板出错: {e}')
                    safe_close_clipboard()
                    return False
                
        except Exception as e:
            log.error(f'清空剪贴板时出错: {e}')
            return False
        finally:
            is_clearing_clipboard = False

def set_clipboard(text):
    """设置剪贴板内容"""
    log.debug('准备设置剪贴板内容...')
    global is_setting_clipboard
    
    with clipboard_lock:  # 使用锁确保线程安全
        try:
            is_setting_clipboard = True
            
            # 使用pyperclip的方式，它已经包含异常处理
            pyperclip.copy(text)
            return True
        except Exception as e:
            log.error(f"设置剪贴板内容出错: {e}")
            return False
        finally:
            is_setting_clipboard = False

# 添加更多剪贴板格式的常量定义
CF_HTML = win32clipboard.RegisterClipboardFormat("HTML Format")
CF_RTF = win32clipboard.RegisterClipboardFormat("Rich Text Format")
CF_URL = win32clipboard.RegisterClipboardFormat("UniformResourceLocator")
CF_OFFICE_DRAWING = win32clipboard.RegisterClipboardFormat("Object Descriptor")

# 添加内容类型识别和操作函数
def is_url(text):
    """检查文本是否为URL"""
    url_pattern = re.compile(
        r'^(https?|ftp)://[^\s/$.?#].[^\s]*$|'
        r'^www\.[^\s/$.?#].[^\s]*$|'
        r'^[^\s/$.?#]+\.(com|net|org|edu|gov|mil|io|co|ai|app|dev|top|xyz)[^\s]*$'
    )
    return url_pattern.match(text) is not None

def is_email(text):
    """检查文本是否为邮箱地址"""
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return email_pattern.match(text) is not None

def open_url(url):
    """打开URL"""
    log.debug(f'准备打开URL: {url}')
    try:
        # 确保URL格式正确
        if not url.startswith(('http://', 'https://', 'ftp://')):
            url = 'https://' + url
        webbrowser.open(url)
        return True
    except Exception as e:
        toast('打开URL失败', '请使用 Debug 版重试并查看日志')
        log.error(f'打开URL失败: {str(e)}')
        return False

def generate_netdisk_path(url: str, pwd: str):
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "jump.pyw"))
    path = path + " --url " + url + " --pwd " + pwd
    return path

def send_email(email):
    """打开默认邮件客户端发送邮件"""
    log.debug('准备打开邮件客户端...')
    try:
        webbrowser.open(f'mailto:{email}')
        return True
    except Exception as e:
        toast('打开邮件客户端失败', '请使用 Debug 版重试并查看日志')
        log.error(f'打开邮件客户端失败: {str(e)}')
        return False

# 修改网盘链接识别相关函数
def detect_netdisk_link(text):
    """
    检测文本中的网盘链接及提取码
    返回格式: {'type': '网盘类型', 'name': '网盘名称', 'url': '链接', 'pwd': '提取码'}
    """
    if not text or not config.get("enable_netdisk_detection", True):
        return None
        
    # 清理文本
    text = text.replace('\u200b', '').strip()
    original_text = text  # 保存原始文本用于提取码检测
    
    # 尝试在原始文本中检测
    result = detect_netdisk_link_raw(text)
    if result:
        return result
    
    # 如果原始文本没有检测到，尝试清理干扰字符后再检测
    cleaned_text = clean_text_for_netdisk_detection(text)
    if cleaned_text != text:  # 确保清理后文本有变化
        result = detect_netdisk_link_raw(cleaned_text)
        if result:
            # 从原始文本中提取提取码
            for disk_type, rule in NETDISK_RULES.items():
                if disk_type == result['type'] and rule['pwd_reg']:
                    pwd_match = re.search(rule['pwd_reg'], original_text)
                    if pwd_match:
                        result['pwd'] = pwd_match.group(1)
                        break
            
            # 如果没找到具体平台的提取码，尝试通用提取码正则
            if not result.get('pwd'):
                general_pwd_match = re.search(r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{3,6})', original_text)
                if general_pwd_match:
                    result['pwd'] = general_pwd_match.group(1)
            return result
    
    return None

def detect_netdisk_link_raw(text):
    """原始网盘链接检测逻辑，从原detect_netdisk_link分离"""
    # 检查每个网盘规则
    for disk_type, rule in NETDISK_RULES.items():
        # 首先匹配基本URL，不包括查询参数
        url_match = re.search(rule['reg'], text)
        if url_match:
            # 获取基本URL
            url_base = url_match.group(0)
            if not url_base.startswith('http'):
                url_base = 'https://' + url_base
            
            # 先检查URL中是否已包含提取码参数
            pwd_from_url = None
            url_pwd_match = re.search(r'[?&]pwd=([a-zA-Z0-9]{4,8})', text)
            if url_pwd_match:
                pwd_from_url = url_pwd_match.group(1)
                
            # 检查文本中是否有单独的提取码
            pwd_from_text = None
            pwd_match = re.search(rule['pwd_reg'], text)
            if pwd_match:
                pwd_from_text = pwd_match.group(1)
            
            # 如果没有找到提取码，尝试使用通用正则
            if not pwd_from_text and not pwd_from_url:
                general_pwd_match = re.search(r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{3,6})', text)
                if general_pwd_match:
                    pwd_from_text = general_pwd_match.group(1)
            
            # 优先使用URL中的提取码
            pwd = pwd_from_url or pwd_from_text
            
            # 获取完整URL，保留原始查询参数
            url = url_base
            url_query_match = re.search(r'^(https?://[^?#]+)(\?.+)$', text)
            if url_query_match and url_pwd_match:
                url = url_query_match.group(0)
            
            return {
                'type': disk_type,
                'name': rule['name'],
                'url': url,
                'pwd': pwd,
                'pwd_in_url': pwd_from_url is not None
            }
    return None

def open_netdisk_with_pwd(url, disk_type, pwd):
    """构建带有提取码的网盘URL并打开"""
    if disk_type in NETDISK_RULES and pwd:
        # 构建包含提取码的URL
        url_template = NETDISK_RULES[disk_type].get('open_with_pwd')
        if url_template:
            url = url_template.format(url=url, pwd=pwd)
    
    # 打开浏览器访问网盘
    webbrowser.open(url)
    
    return url

def open_netdisk_with_pwd_and_copy(netdisk_info):
    """打开网盘链接，并将提取码复制到剪贴板作为后备方案"""
    try:
        url = netdisk_info['url']
        disk_type = netdisk_info['type']
        pwd = netdisk_info.get('pwd')
        pwd_in_url = netdisk_info.get('pwd_in_url', False)
        
        # 1. 如果有提取码且配置允许，复制提取码到剪贴板
        if pwd and config.get("copy_pwd_to_clipboard", True):
            set_clipboard(pwd)
            toast('提取码已复制到剪贴板', f'如自动填充失败，可手动粘贴: {pwd}')
        
        # 2. 构建带提取码的URL，如果URL中已有提取码则不再添加
        if disk_type in NETDISK_RULES and pwd and not pwd_in_url:
            url_template = NETDISK_RULES[disk_type].get('open_with_pwd')
            if url_template and not ('pwd=' in url):
                # 检查URL是否已包含提取码参数
                if not ('pwd=' in url):
                    url = url_template.format(url=url, pwd=pwd)
        
        # 3. 打开浏览器
        webbrowser.open(url)
    except Exception as e:
        toast('打开网盘链接出错', str(e))
        print(f"打开网盘链接出错: {e}")

def get_clipboard_format_name(format_id):
    """安全获取剪贴板格式名称
    
    Args:
        format_id: 格式ID
        
    Returns:
        str: 格式名称，如果出错则返回"未知格式"
    """
    try:
        return win32clipboard.GetClipboardFormatName(format_id)
    except:
        return f"未知格式({format_id})"

def get_clipboard_text():
    """获取剪贴板中的文本内容
    
    Returns:
        str: 文本内容，如果不是文本则返回None
    """
    if not is_clipboard_open():
        if not safe_open_clipboard():
            return None
    
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
            return win32clipboard.GetClipboardData(win32con.CF_TEXT).decode('utf-8')
        else:
            return None
    except Exception as e:
        log.debug(f"获取剪贴板文本出错: {e}")
        return None
    finally:
        # 不关闭剪贴板，由调用者处理
        pass

def get_clipboard_content(truncate=True):
    """获取剪贴板内容及其类型
    
    Args:
        truncate: 是否截断长文本，默认为True
    """
    with clipboard_lock:  # 使用锁确保线程安全
        # 重置此线程的剪贴板状态
        thread_id = threading.get_ident()
        clipboard_open_by_thread[thread_id] = False
        
        for retry in range(MAX_CLIPBOARD_RETRY):
            try:
                # 尝试打开剪贴板
                if not safe_open_clipboard():
                    if retry < MAX_CLIPBOARD_RETRY - 1:
                        time.sleep(CLIPBOARD_RETRY_DELAY)
                        continue
                    else:
                        return {"type": "错误", "content": "无法访问剪贴板，可能被其他程序占用", "raw_content": ""}

                # 检查是否有文本
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT) \
                or win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    try:
                        data = get_clipboard_text()
                        if data is None:
                            raise Exception("无法获取文本数据")
                            
                        safe_close_clipboard()
                        
                        # 检查是否是网盘链接
                        netdisk_info = detect_netdisk_link(data)
                        if (netdisk_info):
                            pwd_info = f" [提取码: {netdisk_info['pwd']}]" if netdisk_info['pwd'] else ""
                            return {
                                "type": "网盘链接", 
                                "content": f"{netdisk_info['name']}: {netdisk_info['url']}{pwd_info}",
                                "netdisk_info": netdisk_info,
                                "raw_content": data  # 保存原始内容
                            }
                        
                        # 检查文本是否是URL
                        if is_url(data):
                            return {
                                "type": "网址", 
                                "content": data if (not truncate or len(data) <= config["truncate_length"]) else data[:config["truncate_length"]] + "...",
                                "raw_content": data  # 保存原始内容
                            }
                        
                        # 检查文本是否是邮箱
                        if is_email(data):
                            return {"type": "邮箱", "content": data, "raw_content": data}
                            
                        return {
                            "type": "文本", 
                            "content": data if (not truncate or len(data) <= config["truncate_length"]) else data[:config["truncate_length"]] + "...",
                            "raw_content": data  # 保存原始内容
                        }
                    except Exception as e:
                        safe_close_clipboard()
                        if retry < MAX_CLIPBOARD_RETRY - 1:
                            time.sleep(CLIPBOARD_RETRY_DELAY)
                            continue
                        log.error(f"获取文本内容出错: {e}")
                        return {"type": "错误", "content": f"获取文本内容出错: {e}", "raw_content": str(e)}
                
                # 检查是否有HTML内容
                elif win32clipboard.IsClipboardFormatAvailable(CF_HTML):
                    try:
                        data = win32clipboard.GetClipboardData(CF_HTML)
                        safe_close_clipboard()
                        # 提取HTML中的纯文本内容摘要
                        import re
                        text = re.sub('<[^<]+?>', '', data)
                        text = ' '.join(text.split())
                        summary = text[:config["truncate_length"]] + "..." if truncate and len(text) > config["truncate_length"] else text
                        return {
                            "type": "HTML", 
                            "content": summary, 
                            "raw_content": data  # 保存原始HTML
                        }
                    except Exception as e:
                        safe_close_clipboard()
                        if retry < MAX_CLIPBOARD_RETRY - 1:
                            time.sleep(CLIPBOARD_RETRY_DELAY)
                            continue
                        return {"type": "HTML", "content": f"HTML内容 (无法显示: {e})", "raw_content": ""}
                
                # 检查是否有RTF格式
                elif win32clipboard.IsClipboardFormatAvailable(CF_RTF):
                    try:
                        data = win32clipboard.GetClipboardData(CF_RTF)
                        safe_close_clipboard()
                        preview = "富文本内容"
                        if len(data) > 50:
                            preview += f" (大小: {len(data)} 字节)"
                        return {"type": "富文本", "content": preview, "raw_content": data}
                    except Exception as e:
                        safe_close_clipboard()
                        if retry < MAX_CLIPBOARD_RETRY - 1:
                            time.sleep(CLIPBOARD_RETRY_DELAY)
                            continue
                        return {"type": "富文本", "content": f"富文本内容 (无法显示: {e})", "raw_content": ""}
                
                # 检查是否有URL
                elif win32clipboard.IsClipboardFormatAvailable(CF_URL):
                    try:
                        url = win32clipboard.GetClipboardData(CF_URL)
                        safe_close_clipboard()
                        return {"type": "网址", "content": url, "raw_content": url}
                    except Exception as e:
                        safe_close_clipboard()
                        if retry < MAX_CLIPBOARD_RETRY - 1:
                            time.sleep(CLIPBOARD_RETRY_DELAY)
                            continue
                        return {"type": "网址", "content": f"网址内容 (无法显示: {e})", "raw_content": ""}
                        
                # 检查是否有图片
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB) or win32clipboard.IsClipboardFormatAvailable(win32con.CF_BITMAP):
                    # 尝试以非直接方式获取图片信息，避免剪贴板访问问题
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                            try:
                                clipboard_formats = []
                                format_id = 0
                                while True:
                                    format_id = win32clipboard.EnumClipboardFormats(format_id)
                                    if format_id == 0:
                                        break
                                    try:
                                        name = get_clipboard_format_name(format_id)
                                        clipboard_formats.append(f"{name}")
                                    except:
                                        pass
                                
                                safe_close_clipboard()
                                # 使用通用描述而不是尝试获取DIB数据
                                return {"type": "图片", "content": f"已复制一张图片", "raw_content": "image"}
                            except Exception as e:
                                log.debug(f"获取DIB格式图片信息失败: {e}")
                                safe_close_clipboard()
                                return {"type": "图片", "content": "已复制一张图片", "raw_content": ""}
                        else:
                            safe_close_clipboard()
                            return {"type": "图片", "content": "已复制一张图片", "raw_content": ""}
                    except Exception as e:
                        safe_close_clipboard()
                        log.debug(f"处理图片剪贴板内容时出错: {e}")
                        return {"type": "图片", "content": "已复制一张图片", "raw_content": ""}
                    
                # 检查是否有文件列表
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    try:
                        file_list = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                        safe_close_clipboard()
                        
                        file_count = len(file_list)
                        if file_count == 1:
                            file_path = file_list[0]
                            file_name = os.path.basename(file_path)
                            try:
                                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                            except:
                                file_size = 0
                            
                            # 格式化文件大小
                            if file_size < 1024:
                                size_str = f"{file_size} 字节"
                            elif file_size < 1024 * 1024:
                                size_str = f"{file_size/1024:.1f} KB"
                            else:
                                size_str = f"{file_size/(1024*1024):.1f} MB"
                                
                            return {"type": "文件", "content": f"已复制文件: {file_name} ({size_str})", "raw_content": file_path}
                        else:
                            return {"type": "文件", "content": f"已复制 {file_count} 个文件", "raw_content": file_list}
                    except Exception as e:
                        safe_close_clipboard()
                        if retry < MAX_CLIPBOARD_RETRY - 1:
                            time.sleep(CLIPBOARD_RETRY_DELAY)
                            continue
                        return {"type": "文件", "content": f"文件内容 (无法显示: {e})", "raw_content": ""}
                
                # 检查是否是Office绘图对象
                elif win32clipboard.IsClipboardFormatAvailable(CF_OFFICE_DRAWING):
                    safe_close_clipboard()
                    return {"type": "Office对象", "content": "已复制Office绘图或对象", "raw_content": ""}
                    
                # 其他格式
                else:
                    try:
                        clipboard_formats = []
                        format_id = 0
                        
                        while True:
                            try:
                                format_id = win32clipboard.EnumClipboardFormats(format_id)
                                if format_id == 0:
                                    break
                                    
                                # 尝试获取格式名称
                                name = get_clipboard_format_name(format_id)
                                clipboard_formats.append(f"{name} ({format_id})")
                            except:
                                break
                        
                        safe_close_clipboard()
                        
                        if clipboard_formats:
                            return {"type": "特殊格式", "content": f"已复制内容 (格式: {', '.join(clipboard_formats[:3])}...)", "raw_content": clipboard_formats}
                        else:
                            return {"type": "未知格式", "content": "已复制内容 (未知格式)", "raw_content": ""}
                    except Exception as e:
                        safe_close_clipboard()
                        if retry < MAX_CLIPBOARD_RETRY - 1:
                            time.sleep(CLIPBOARD_RETRY_DELAY)
                            continue
                        return {"type": "未知格式", "content": f"未知格式 (出错: {e})", "raw_content": ""}

            except Exception as e:
                # 确保剪贴板被关闭
                try:
                    safe_close_clipboard()
                except:
                    pass
                
                if retry < MAX_CLIPBOARD_RETRY - 1:
                    time.sleep(CLIPBOARD_RETRY_DELAY)
                    continue
                else:
                    log.error(f"获取剪贴板内容异常: {e}")
                    return {"type": "错误", "content": f"获取剪贴板内容异常: {e}", "raw_content": str(e)}
                    
        # 所有重试都失败
        return {"type": "错误", "content": "多次尝试获取剪贴板内容失败", "raw_content": ""}

# 创建系统托盘图标
def create_image():
    """创建一个简单的系统托盘图标"""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color='white')
    dc = ImageDraw.Draw(image)
    dc.rectangle([(15, 15), (width-15, height-15)], outline='black', fill='lightblue')
    dc.text((20, 35), "CB", fill='black')
    return image

def setup_tray_icon():
    """设置系统托盘图标和菜单"""
    
    # 创建菜单
    def create_menu():
        return pystray.Menu(
            pystray.MenuItem('清空当前剪贴板', lambda: clear_clipboard()),
            pystray.MenuItem('网盘链接检测', lambda: toggle_netdisk_detection()),
            pystray.MenuItem('访问网盘时复制提取码', lambda: toggle_copy_pwd()),
            pystray.MenuItem('注册网盘协议处理器', lambda: request_admin_and_register()),
            pystray.MenuItem('退出', lambda: icon.stop())
        )
    
    # 创建图标
    try:
        # 尝试从静态文件加载图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "favicon.ico")
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
        else:
            # 如果文件不存在，则创建一个简单的图标
            image = create_image()
    except:
        image = create_image()
        
    # 正确调用create_menu()函数获取菜单对象
    icon = pystray.Icon("clipboard_monitor", image, "剪贴板监视器", create_menu())
    
    return icon

def toggle_netdisk_detection():
    """切换网盘链接检测功能的开关"""
    config["enable_netdisk_detection"] = not config.get("enable_netdisk_detection", True)
    save_config()
    toast(
        "网盘链接检测",
        f"已{'启用' if config['enable_netdisk_detection'] else '禁用'}网盘链接检测功能"
    )

def toggle_copy_pwd():
    """切换打开网盘时是否复制提取码到剪贴板"""
    config["copy_pwd_to_clipboard"] = not config.get("copy_pwd_to_clipboard", True)
    save_config()
    toast(
        "复制提取码功能",
        f"打开网盘时{'会' if config['copy_pwd_to_clipboard'] else '不会'}自动复制提取码到剪贴板"
    )

def generate_netdisk_uri(url, pwd=None):
    """生成网盘URI，使用netdisk://协议"""
    if pwd:
        return f"netdisk://{url}?pwd={pwd}"
    else:
        return f"netdisk://{url}"

def handle_netdisk_link(url, pwd=None):
    """处理网盘链接，提供访问选项"""
    try:
        # 如果有提取码，构建完整URL
        if pwd:
            # 尝试打开我们的自定义协议
            webbrowser.open(generate_netdisk_uri(url, pwd))
        else:
            # 没有提取码，直接打开链接
            webbrowser.open(url)
        return True
    except Exception as e:
        toast('打开网盘链接失败', str(e))
        return False

def monitor_clipboard():
    """监视剪贴板变化的主函数"""
    global previous_content
    
    # 初始化剪贴板监视
    previous_content = get_clipboard_content(truncate=True)
    
    # 持续监视剪贴板
    toast(
        "Clipboard Enhance 已启动",
        "监听剪贴板中..."
    )
    try:
        while True:
            # 如果正在清空或设置剪贴板，跳过这次检查
            if is_clearing_clipboard or is_setting_clipboard:
                time.sleep(config["check_interval"])
                continue
                
            current_content = get_clipboard_content(truncate=True)  # 通知显示使用截断内容
            if current_content != previous_content:
                previous_content = current_content
                
                # 如果启用了通知
                if config["show_notifications"]:
                    content_type = current_content["type"]
                    content_value = current_content["content"]
                    
                    # 根据内容类型设置不同的通知和按钮
                    if content_type == "网盘链接":
                        netdisk_info = current_content.get("netdisk_info", {})
                        pwd_text = f"提取码：{netdisk_info['pwd']}" if netdisk_info.get('pwd') else "未检测到提取码"
                        
                        # 构建带提取码的URL
                        url = netdisk_info['url']
                        pwd = netdisk_info.get('pwd')
                        
                        # 创建通知按钮
                        buttons = []
                        if pwd:
                            # 添加访问网盘按钮 (使用netdisk://协议)
                            buttons.append({
                                'activationType': 'protocol', 
                                'content': '访问网盘', 
                                'arguments': generate_netdisk_uri(url, pwd)
                            })
                            
                            # 添加仅复制提取码按钮
                            buttons.append({
                                'activationType': 'background', 
                                'content': '复制提取码', 
                                'arguments': 'copy_pwd'
                            })
                        else:
                            # 没有提取码，只添加普通访问按钮
                            buttons.append({
                                'activationType': 'protocol', 
                                'content': '访问网盘', 
                                'arguments': url
                            })
                        
                        # 创建通知
                        notify(
                            f'已复制{netdisk_info["name"]}链接',
                            f"{netdisk_info['url']}\n{pwd_text}\n\n点击通知可清空剪贴板",
                            on_click=lambda args: clear_clipboard(),
                            buttons=buttons
                        )
                    
                    elif content_type == "网址":
                        notify(
                            f'复制成功 (网址)',
                            content_value + "\n\n点击通知可清空剪贴板",
                            on_click=lambda args: clear_clipboard(),
                            buttons=[
                                {'activationType': 'protocol', 'content': '访问', 'arguments': content_value}
                            ]
                        )
                    elif content_type == "邮箱":
                        notify(
                            f'复制成功 (邮箱)',
                            content_value + "\n\n点击通知可清空剪贴板",
                            on_click=lambda args: clear_clipboard(),
                            buttons=[
                                {'activationType': 'protocol', 'content': '发送邮件', 'arguments': f'mailto:{content_value}'}
                            ]
                        )
                    else:
                        # 对于其他类型，使用常规通知
                        toast(
                            f'复制成功 ({content_type})', 
                            content_value + "\n\n点击此通知可清空剪贴板",
                            on_click=lambda args: clear_clipboard()
                        )
            time.sleep(config["check_interval"])  # 使用配置的检查间隔
    except KeyboardInterrupt:
        print("程序已退出。")
        
    # 退出时清理临时文件
    try:
        temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_netdisk.json")
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except:
        pass

def handle_notification_action(args, pwd=None):
    """处理通知按钮点击"""
    if args == 'copy_pwd' and pwd:
        # 复制提取码到剪贴板
        set_clipboard(pwd)
        toast('提取码已复制到剪贴板', f'提取码: {pwd}')
        return True
    return False

# ==== 网盘协议处理功能（从netdisk.py集成） ====
def handle_netdisk_protocol(
    url: str = None,
    pwd: str = None,
    register: bool = False
):
    """处理netdisk://协议请求（命令行处理入口点）"""
    
    log.debug(f"处理协议请求: url={url}, pwd={pwd}, register={register}")
    
    # 处理注册协议请求
    if register:
        request_admin_and_register()
        exit_application(code=1)
        
    # 没有URL参数，退出
    if not url:
        log.error("缺少必要的URL参数")
        exit_application(code=1)
    
    # 去除可能存在的引号
    url = url.strip('"')
    
    # 处理URL，移除netdisk://前缀并确保协议格式正确
    if url.startswith("netdisk://"):
        url = url[len("netdisk://"):]
        
    # 确保URL包含正确的协议格式
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    
    # 修复重复的查询参数问题
    # 如果URL包含多个问号，只保留第一个问号
    question_mark_pos = url.find('?')
    if question_mark_pos > 0 and url.find('?', question_mark_pos + 1) > 0:
        url = url[:question_mark_pos] + '?' + url[question_mark_pos + 1:].replace('?', '&')
        log.debug(f"修复后的URL: {url}")
    
    # 从URL中提取提取码 (如果存在)
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'pwd' in query_params and not pwd:
            # 获取提取码，并确保不包含额外的pwd参数
            extracted_pwd = query_params['pwd'][0]
            
            # 清理提取码中可能的额外pwd参数
            if '?pwd=' in extracted_pwd or '&pwd=' in extracted_pwd:
                extracted_pwd = extracted_pwd.split('?pwd=')[0].split('&pwd=')[0]
                log.debug(f"清理后的提取码: {extracted_pwd}")
            
            pwd = extracted_pwd
            log.debug(f"从URL中提取到提取码: {pwd}")
            
            # 从URL中移除pwd参数
            clean_params = {k: v[0] for k, v in query_params.items() if k != 'pwd'}
            clean_query = "&".join([f"{k}={v}" for k, v in clean_params.items()])
            
            url_parts = list(parsed_url)
            url_parts[4] = clean_query
            url = urlunparse(url_parts)
    
    except Exception as e:
        log.error(f"解析URL时出错: {e}")
    
    log.debug(f"最终URL: {url}, 提取码: {pwd}")
    
    # 打开网盘链接
    webbrowser.open(url)
    
    # 如果有提取码，复制到剪贴板
    if pwd:
        pyperclip.copy(pwd)
        toast('提取码已复制到剪贴板', f'如自动填充失败，可手动粘贴: {pwd}')
    
    # 使用exit_application确保程序能够正确退出
    exit_application()

# ==== 协议注册功能（从register_protocol.py集成） ====
def register_netdisk_protocol():
    """注册 netdisk:// 协议处理器"""
    try:
        # 使用当前可执行文件路径，而不是Python解释器
        executable_path = sys.executable
        
        # 对于已打包的EXE文件，直接使用可执行文件作为处理程序
        # 确保传递的参数格式正确
        command = f'"{executable_path}" -url "%1"'
        
        # 创建注册表项
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "netdisk") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "URL:Netdisk Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            with winreg.CreateKey(key, "shell\\open\\command") as cmd_key:
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, command)
        
        toast("协议注册成功", "现在可以使用 netdisk:// 链接打开网盘")
        return True
    
    except Exception as e:
        toast("协议注册失败", str(e))
        log.error(f"注册协议处理器失败: {e}")
        return False

def request_admin_and_register():
    """请求管理员权限并注册协议"""
    # 检查是否已有管理员权限
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
        
    if is_admin:
        # 已经有管理员权限，直接注册
        register_netdisk_protocol()
        exit_application()
    else:
        toast(
        "请关闭本应用并以管理员身份启动",
        "注册协议时遇到问题：权限不足，拒绝访问"
    )

def main():
    # 作为主程序运行
    import pystray
    import threading
    import clipboard_preview
    from PyQt5.QtCore import QTimer
    
    # 加载配置
    load_config()
    
    # 初始化QApplication
    log.debug('初始化QApplication...')
    app = QApplication([]) if not QApplication.instance() else QApplication.instance()
    
    # 启动剪贴板监视线程
    log.debug('启动剪贴板监视线程...')
    monitor_thread = threading.Thread(target=monitor_clipboard, daemon=True)
    monitor_thread.start()
    
    # 初始化剪贴板预览控制器（在主线程中）
    preview_controller = clipboard_preview.ClipboardPreviewController(lambda: get_clipboard_content(truncate=False))
    preview_controller.setup(app)
    
    # 显示系统托盘图标
    icon = setup_tray_icon()
    
    # 修改托盘菜单，添加注册协议选项，并更新退出功能
    def create_menu():
        return pystray.Menu(
            pystray.MenuItem('清空当前剪贴板', lambda: clear_clipboard()),
            pystray.MenuItem('网盘链接检测', lambda: toggle_netdisk_detection()),
            pystray.MenuItem('访问网盘时复制提取码', lambda: toggle_copy_pwd()),
            pystray.MenuItem('注册网盘协议处理器', lambda: request_admin_and_register()),
            pystray.MenuItem('退出', lambda: exit_application(icon=icon, app=app))
        )
    
    icon.menu = create_menu()
    
    # 使用QTimer定期处理事件，而不是在pystray的回调中这样做
    qt_timer = QTimer()
    qt_timer.timeout.connect(app.processEvents)
    qt_timer.start(100)
    
    # 以非阻塞方式启动pystray
    icon_thread = threading.Thread(target=icon.run, daemon=True)
    icon_thread.start()
    
    # 启动Qt事件循环（主循环）
    sys.exit(app.exec_())        

# 创建完全退出程序的函数
def exit_application(code: int = 0, icon: Icon = None, app: QApplication = None):
    # 检查是否提供了icon和app参数
    if icon is not None:
        # 停止托盘图标
        icon.stop()
    if app is not None:
        # 退出Qt应用程序
        app.quit()
    
    pid = os.getpid()
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
    except Exception as e:
        print(f"强制终止失败: {e}")
        os._exit(1)    # 强制终止