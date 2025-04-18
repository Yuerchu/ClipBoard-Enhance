import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPixmap, QImage
import win32api
import win32gui  # 添加 win32gui 模块
import keyboard
import win32con
import threading

class ClipboardSignals(QObject):
    """用于线程间通信的信号"""
    update_preview = pyqtSignal(dict)
    show_preview = pyqtSignal()
    hide_preview = pyqtSignal()

class PreviewWindow(QMainWindow):
    """无边框窗口，用于预览剪贴板内容"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.fade_timer = None
        self.opacity = 0.0
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('剪贴板预览')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # 创建主窗口部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # 设置布局
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建标题标签
        self.title_label = QLabel("剪贴板内容")
        self.title_label.setStyleSheet("color: white; font-weight: bold;")
        self.layout.addWidget(self.title_label)
        
        # 创建内容标签
        self.content_label = QLabel()
        self.content_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0);")
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_label.setMinimumWidth(200)
        self.content_label.setMaximumWidth(400)
        self.layout.addWidget(self.content_label)
        
        # 设置样式
        central_widget.setStyleSheet("""
            background-color: rgba(30, 30, 30, 220);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 30);
        """)
        
        # 设置初始透明度
        self.setWindowOpacity(0.0)

    def update_content(self, content):
        """更新窗口内容"""
        if not content:
            return
            
        content_type = content.get("type", "未知")
        content_value = content.get("content", "")
        
        self.title_label.setText(f"剪贴板内容 - {content_type}")
        
        if content_type == "图片":
            # 图片内容，显示预览
            try:
                if isinstance(content_value, dict) and "bitmap" in content_value:
                    # 处理bitmap数据
                    pixmap = QPixmap.fromImage(content_value["bitmap"])
                    # 调整图片大小
                    if pixmap.width() > 350:
                        pixmap = pixmap.scaledToWidth(350, Qt.SmoothTransformation)
                    if pixmap.height() > 250:
                        pixmap = pixmap.scaledToHeight(250, Qt.SmoothTransformation)
                    self.content_label.setPixmap(pixmap)
                else:
                    # 显示文本描述
                    self.content_label.setText(content_value)
            except Exception as e:
                self.content_label.setText(f"图片预览错误: {str(e)}")
        else:
            # 文本内容
            self.content_label.setPixmap(QPixmap())  # 清除之前的图片
            if isinstance(content_value, str):
                if len(content_value) > 500:
                    content_value = content_value[:500] + "..."
                self.content_label.setText(content_value)
            else:
                self.content_label.setText(str(content_value))
        
        # 调整窗口大小以适应内容
        self.adjustSize()
    
    def position_at_cursor(self):
        """将窗口定位到鼠标光标位置附近"""
        cursor_pos = QPoint(*win32api.GetCursorPos())
        screen = QDesktopWidget().screenGeometry()
        
        # 计算水平位置，避免窗口超出屏幕
        if cursor_pos.x() + self.width() > screen.width():
            x = screen.width() - self.width()
        else:
            x = cursor_pos.x()
            
        # 计算垂直位置，在光标下方显示，除非超出屏幕底部
        if cursor_pos.y() + 20 + self.height() > screen.height():
            y = cursor_pos.y() - self.height() - 10
        else:
            y = cursor_pos.y() + 20
            
        self.move(x, y)
    
    def show_with_fade(self):
        """使用淡入效果显示窗口"""
        # 定位窗口位置
        self.position_at_cursor()
        
        self.opacity = 0.0
        self.setWindowOpacity(self.opacity)
        self.show()
        
        # 如果计时器已经存在，先停止
        if self.fade_timer:
            self.fade_timer.stop()
            
        # 创建动画计时器
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_in_step)
        self.fade_timer.start(20)  # 每20毫秒更新一次
    
    def fade_in_step(self):
        """逐步增加透明度"""
        self.opacity += 0.1
        if self.opacity >= 1.0:
            self.opacity = 1.0
            self.fade_timer.stop()
        self.setWindowOpacity(self.opacity)

class ClipboardPreviewController(QObject):
    """控制剪贴板预览窗口的显示和隐藏"""
    
    def __init__(self, get_clipboard_func):
        super().__init__()
        self.get_clipboard_content = get_clipboard_func
        self.signals = ClipboardSignals()
        self.preview_window = None
        self.ctrl_pressed = False
        self.preview_timer = None
        self.clipboard_content = None
        
    def setup(self, app):
        """初始化控制器"""
        self.app = app
        
        # 创建预览窗口（在主线程中）
        self.preview_window = PreviewWindow()
        
        # 连接信号
        self.signals.update_preview.connect(self.update_preview_window)
        self.signals.show_preview.connect(self.show_preview_window)
        self.signals.hide_preview.connect(self.hide_preview_window)
        
        # 启动键盘监听线程
        self.keyboard_thread = threading.Thread(target=self.keyboard_monitor, daemon=True)
        self.keyboard_thread.start()
    
    def keyboard_monitor(self):
        """在单独的线程中监听键盘事件"""
        try:
            # 使用keyboard库监听Ctrl键，更简单可靠
            keyboard.on_press_key("ctrl", self.kb_on_ctrl_pressed)
            keyboard.on_release_key("ctrl", self.kb_on_ctrl_released)
            print("使用keyboard库监听Ctrl键")
            
            # 以下代码保留但不再使用，因为win32gui的热键监听在多线程环境中可能不稳定
            """
            # 注册全局热键 (Ctrl)
            ctrl_down_id = 1
            ctrl_up_id = 2
            
            if win32gui.RegisterHotKey(None, ctrl_down_id, 0, win32con.VK_CONTROL):
                print("Ctrl键监听已启动")
            else:
                print("Ctrl键监听启动失败")
                
            if win32gui.RegisterHotKey(None, ctrl_up_id, win32con.MOD_CONTROL, win32con.VK_CONTROL):
                print("Ctrl键释放监听已启动")
            else:
                print("Ctrl键释放监听启动失败")
                
            # 消息循环
            try:
                msg = win32gui.GetMessage(None, 0, 0)
                while msg:
                    if msg[1][0] == ctrl_down_id:
                        self.on_ctrl_pressed()
                    elif msg[1][0] == ctrl_up_id:
                        self.on_ctrl_released()
                    msg = win32gui.GetMessage(None, 0, 0)
            finally:
                win32gui.UnregisterHotKey(None, ctrl_down_id)
                win32gui.UnregisterHotKey(None, ctrl_up_id)
            """
        except Exception as e:
            print(f"键盘监听错误: {e}")
            
            # 确保即使出错也能启用键盘监听
            try:
                keyboard.on_press_key("ctrl", self.kb_on_ctrl_pressed)
                keyboard.on_release_key("ctrl", self.kb_on_ctrl_released)
                print("降级到keyboard库监听")
            except Exception as e2:
                print(f"键盘监听完全失败: {e2}")
    
    def on_ctrl_pressed(self):
        """Ctrl键被按下时的处理函数"""
        if not self.ctrl_pressed:
            self.ctrl_pressed = True
            if self.preview_timer:
                self.preview_timer.cancel()
            self.preview_timer = threading.Timer(0.5, self.prepare_preview)
            self.preview_timer.start()
    
    def on_ctrl_released(self):
        """Ctrl键被释放时的处理函数"""
        self.ctrl_pressed = False
        if self.preview_timer:
            self.preview_timer.cancel()
            self.preview_timer = None
        self.signals.hide_preview.emit()
    
    def kb_on_ctrl_pressed(self, event):
        """键盘库的Ctrl按下处理"""
        self.on_ctrl_pressed()
    
    def kb_on_ctrl_released(self, event):
        """键盘库的Ctrl释放处理"""
        self.on_ctrl_released()
    
    def prepare_preview(self):
        """获取剪贴板内容并准备预览"""
        if self.ctrl_pressed:
            try:
                content = self.get_clipboard_content()
                self.signals.update_preview.emit(content)
                self.signals.show_preview.emit()
            except Exception as e:
                print(f"预览准备错误: {e}")
    
    def update_preview_window(self, content):
        """更新预览窗口内容（在主线程中执行）"""
        if self.preview_window:
            self.preview_window.update_content(content)
    
    def show_preview_window(self):
        """显示预览窗口（在主线程中执行）"""
        if self.preview_window and self.ctrl_pressed:
            self.preview_window.show_with_fade()
    
    def hide_preview_window(self):
        """隐藏预览窗口（在主线程中执行）"""
        if self.preview_window:
            self.preview_window.hide()
