import clipboard_preview
from func import (
    clear_clipboard, 
    get_clipboard_content, 
    handle_netdisk_protocol, 
    load_config,
    monitor_clipboard,
    request_admin_and_register, 
    setup_tray_icon,
    toggle_copy_pwd, toggle_netdisk_detection
)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import sys
import pystray
import threading

# Clipboard_preview.py
import os
from PyQt5.QtWidgets import (QLabel, QMainWindow, QVBoxLayout, 
                            QWidget, QDesktopWidget, QScrollArea, QPushButton,
                            QHBoxLayout, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QObject, QEvent
from PyQt5.QtGui import QPixmap, QFontDatabase
import win32api
import keyboard

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and (any('--url' in arg for arg in sys.argv) \
    or any('--register' in arg for arg in sys.argv)):
        # 作为协议处理器运行
        handle_netdisk_protocol()
        sys.exit(0)
        
    # 作为主程序运行
    # 加载配置
    load_config()
    
    # 初始化QApplication
    app = QApplication([]) if not QApplication.instance() else QApplication.instance()
    
    # 启动剪贴板监视线程
    monitor_thread = threading.Thread(target=monitor_clipboard, daemon=True)
    monitor_thread.start()
    
    # 初始化剪贴板预览控制器（在主线程中）
    preview_controller = clipboard_preview.ClipboardPreviewController(lambda: get_clipboard_content(truncate=False))
    preview_controller.setup(app)
    
    # 显示系统托盘图标
    icon = setup_tray_icon()
    
    # 修改托盘菜单，添加注册协议选项
    def create_menu():
        return pystray.Menu(
            pystray.MenuItem('清空当前剪贴板', lambda: clear_clipboard()),
            pystray.MenuItem('网盘链接检测', lambda: toggle_netdisk_detection()),
            pystray.MenuItem('访问网盘时复制提取码', lambda: toggle_copy_pwd()),
            pystray.MenuItem('注册网盘协议处理器', lambda: request_admin_and_register()),
            pystray.MenuItem('退出', lambda: icon.stop())
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