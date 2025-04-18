import sys
import os
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QVBoxLayout, 
                            QWidget, QDesktopWidget, QScrollArea, QPushButton,
                            QHBoxLayout, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QSize, QEvent
from PyQt5.QtGui import QFont, QPixmap, QImage, QIcon, QPalette, QColor, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QFontDatabase, QWheelEvent
import win32api
import keyboard
import win32con
import threading
import re

# 尝试导入语法高亮库
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

class ClipboardSignals(QObject):
    """用于线程间通信的信号"""
    update_preview = pyqtSignal(dict)
    show_preview = pyqtSignal()
    hide_preview = pyqtSignal()

class CodeDetector:
    """检测文本是否是代码，并尝试识别语言"""
    
    @staticmethod
    def is_code(text):
        """判断文本是否可能是代码"""
        # 检查一些常见的代码特征
        code_patterns = [
            r'(def|class|import|from|function)\s+\w+',  # Python, JavaScript
            r'(public|private|protected)\s+(static\s+)?(void|int|string|bool|class)',  # Java, C#, C++
            r'(var|let|const)\s+\w+\s*=',  # JavaScript
            r'(#include|#define)',  # C/C++
            r'<[a-z]+(\s+[a-z\-]+="[^"]*")*>',  # HTML tags
            r'@[a-zA-Z]+(\([^)]*\))?',  # Java/C# annotations
            r'^\s*[a-zA-Z_][a-zA-Z0-9_]*:\s',  # YAML
            r'^\s*"[^"]*":\s',  # JSON
            r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s=\s',  # config files
            r'SELECT\s+.+\s+FROM\s+\w+',  # SQL
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                return True
                
        # 检查特定符号的分布
        symbols = ['{', '}', '(', ')', '[', ']', ';', ':', '=', '+', '-', '*', '/', '%']
        symbol_count = sum(text.count(s) for s in symbols)
        lines = text.count('\n') + 1
        
        # 如果多行文本中符号比较密集，很可能是代码
        if lines > 2 and symbol_count / len(text) > 0.05:
            return True
            
        return False
    
    @staticmethod
    def detect_language(text):
        """尝试检测代码的语言"""
        if not PYGMENTS_AVAILABLE:
            return "text"
            
        try:
            lexer = guess_lexer(text)
            return lexer.name.lower()
        except:
            return "text"

class StyleSheet:
    """应用程序的样式定义"""
    
    # 加载自定义字体
    FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "MapleMono-NF-CN-Regular.ttf")
    FONT_LOADED = False
    FONT_NAME = "Maple Mono NF CN"
    
    @classmethod
    def load_custom_font(cls):
        """加载自定义字体"""
        if cls.FONT_LOADED:
            return True
            
        try:
            if os.path.exists(cls.FONT_PATH):
                font_id = QFontDatabase.addApplicationFont(cls.FONT_PATH)
                if font_id != -1:
                    cls.FONT_LOADED = True
                    cls.FONT_FAMILY = QFontDatabase.applicationFontFamilies(font_id)[0]
                    print(f"已加载自定义字体: {cls.FONT_FAMILY}")
                    return True
        except Exception as e:
            print(f"加载字体失败: {e}")
        
        return False
    
    # 基础样式
    @classmethod
    def get_base_style(cls):
        """获取基础样式，根据字体加载情况动态生成"""
        cls.load_custom_font()
        
        if cls.FONT_LOADED:
            return f"""
                QWidget {{
                    font-family: '{cls.FONT_FAMILY}', 'Segoe UI', Arial, sans-serif;
                }}
                
                QLabel {{
                    color: #e0e0e0;
                }}
            """
        else:
            return """
                QWidget {
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                
                QLabel {
                    color: #e0e0e0;
                }
            """
    
    # 主窗口样式
    MAIN_WINDOW = """
        background-color: rgba(40, 40, 40, 240);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 30);
    """
    
    # 标题栏样式
    TITLE_BAR = """
        background-color: rgba(60, 60, 60, 200);
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        padding: 5px;
    """
    
    # 标题样式
    TITLE = """
        font-weight: bold;
        font-size: 15px;
        color: #ffffff;
        padding-left: 5px;
    """
    
    # 内容区域样式
    CONTENT_AREA = """
        background-color: transparent;
        padding: 8px;
    """
    
    # 内容标签样式
    @classmethod
    def get_content_label_style(cls):
        """获取内容标签样式，针对代码应用自定义字体"""
        cls.load_custom_font()
        
        base_style = """
            color: #e0e0e0;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background-color: rgba(0, 0, 0, 20);
        """
        
        if cls.FONT_LOADED:
            return base_style + f"""
                pre, code, .highlight {{
                    font-family: '{cls.FONT_FAMILY}', 'Consolas', 'Courier New', monospace;
                }}
            """
        else:
            return base_style + """
                pre, code, .highlight {
                    font-family: 'Consolas', 'Courier New', monospace;
                }
            """
    
    # 滚动区域样式
    SCROLL_AREA = """
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        
        QScrollBar:vertical {
            border: none;
            background: rgba(60, 60, 60, 100);
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: rgba(180, 180, 180, 150);
            min-height: 24px;
            border-radius: 6px;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        
        QScrollBar:horizontal {
            border: none;
            background: rgba(60, 60, 60, 100);
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background: rgba(180, 180, 180, 150);
            min-width: 24px;
            border-radius: 6px;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
    """
    
    # 按钮样式
    BUTTON = """
        QPushButton {
            background-color: rgba(70, 130, 180, 150);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 5px;
            font-size: 12px;
        }
        
        QPushButton:hover {
            background-color: rgba(70, 130, 180, 200);
        }
        
        QPushButton:pressed {
            background-color: rgba(70, 130, 180, 220);
        }
    """
    
    # 不同类型内容的强调色
    TYPE_COLORS = {
        "文本": "#e0e0e0",
        "网址": "#4fc3f7",
        "邮箱": "#81c784",
        "网盘链接": "#ffb74d",
        "图片": "#ba68c8",
        "文件": "#4db6ac",
        "HTML": "#f06292",
        "富文本": "#9575cd",
        "代码": "#fff176",
        "Office对象": "#7986cb",
        "错误": "#ef5350",
        "特殊格式": "#ffab91",
        "未知格式": "#b0bec5"
    }

class ScrollAreaWithWheelEvents(QScrollArea):
    """扩展的滚动区域，支持按住Ctrl时的鼠标滚轮事件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(StyleSheet.SCROLL_AREA)
        self.horizontalScrollValue = 0
        
        # 设置焦点策略，使其能够接收鼠标滚轮事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 安装事件过滤器以处理滚轮事件
        self.installEventFilter(self)
        
    def wheelEvent(self, event):
        """处理鼠标滚轮事件"""
        # 检查是否按下了Ctrl键
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers == Qt.ControlModifier:
            # 如果按下Ctrl，根据鼠标滚轮方向和不同的modifier决定滚动方向
            if event.angleDelta().y() != 0:
                # 垂直滚动 - 确保值为整数
                delta = int(event.angleDelta().y() / 2)  # 转换为整数
                current_value = self.verticalScrollBar().value()
                self.verticalScrollBar().setValue(current_value - delta)
            
            # 如果按下Alt+Ctrl，或者按下Shift+Ctrl，或者水平滚动量不为0
            elif event.angleDelta().x() != 0 or modifiers & Qt.AltModifier or modifiers & Qt.ShiftModifier:
                # 水平滚动 - 确保值为整数
                if event.angleDelta().x() != 0:
                    delta = int(event.angleDelta().x() / 2)
                else:
                    delta = int(-event.angleDelta().y() / 2)
                
                current_value = self.horizontalScrollBar().value()
                self.horizontalScrollBar().setValue(current_value - delta)
                
            event.accept()
        else:
            # 如果没有按下Ctrl，使用默认行为
            super().wheelEvent(event)
            
    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获并处理事件"""
        if event.type() == QEvent.Wheel:
            # 特别处理滚轮事件，确保它们直接传递给滚动区域
            self.wheelEvent(event)
            return True
        return super().eventFilter(obj, event)

class ContentWidget(QFrame):
    """内容显示窗口部件，根据内容类型显示不同的格式"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 创建内容容器部件，用于包含内容标签
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setAlignment(Qt.AlignTop)  # 确保内容顶部对齐
        
        # 创建内容标签
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # 允许垂直扩展
        self.content_label.setStyleSheet(StyleSheet.get_content_label_style())
        self.content_label.setMinimumWidth(300)
        
        # 添加标签到容器
        self.content_layout.addWidget(self.content_label)
        
        # 为了确保滚动区域知道内容的实际大小，我们需要设置一些额外的属性
        self.content_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 创建增强的滚动区域
        self.scroll_area = ScrollAreaWithWheelEvents()
        self.scroll_area.setWidgetResizable(True)  # 确保设置了这个属性
        self.scroll_area.setWidget(self.content_container)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(StyleSheet.SCROLL_AREA)
        
        # 默认显示滚动条，即使内容不需要滚动
        # self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # 添加到布局
        self.layout.addWidget(self.scroll_area)
        
        # 创建操作按钮区域
        self.action_layout = QHBoxLayout()
        self.action_layout.setContentsMargins(0, 5, 0, 0)
        self.action_layout.setSpacing(10)
        
        # 展开/折叠按钮
        self.expand_button = QPushButton("展开全部")
        self.expand_button.clicked.connect(self.toggle_expand)
        self.expand_button.setStyleSheet(StyleSheet.BUTTON)
        self.expand_button.setVisible(False)
        self.action_layout.addWidget(self.expand_button)
        
        # 右侧空白占位
        self.action_layout.addStretch(1)
        
        # 添加操作按钮布局
        self.layout.addLayout(self.action_layout)
        
        # 默认不展开
        self.is_expanded = False
        self.full_content = ""
        self.truncated_content = ""
        
        # 设置样式
        self.setStyleSheet("background-color: transparent;")
    
    def set_content(self, content_type, content_value):
        """设置内容，根据类型进行适当处理"""
        self.content_type = content_type
        
        # 清除之前的内容
        self.content_label.setText("")
        self.content_label.setPixmap(QPixmap())
        
        # 设置标签颜色
        color = StyleSheet.TYPE_COLORS.get(content_type, "#e0e0e0")
        self.content_label.setStyleSheet(f"{StyleSheet.get_content_label_style()}; color: {color};")
        
        # 优先使用原始内容（如果有的话）
        if isinstance(content_value, dict) and "raw_content" in content_value:
            actual_content = content_value["raw_content"]
        else:
            actual_content = content_value
        
        # 根据内容类型处理
        if content_type == "图片":
            self.handle_image(content_value)
        elif content_type in ["网址", "邮箱", "网盘链接"]:
            self.handle_link(actual_content)
        elif content_type == "HTML":
            if isinstance(content_value, dict) and "raw_content" in content_value:
                self.handle_html(content_value["raw_content"])
            else:
                self.handle_html(actual_content)
        elif content_type == "文本" and len(actual_content) > 30:
            # 检测是否为代码
            if CodeDetector.is_code(actual_content):
                self.handle_code(actual_content)
            else:
                self.handle_long_text(actual_content)
        else:
            self.handle_text(actual_content)
    
    def handle_image(self, content):
        """处理图片内容"""
        if isinstance(content, dict) and "bitmap" in content:
            pixmap = QPixmap.fromImage(content["bitmap"])
            pixmap = pixmap.scaled(350, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.content_label.setPixmap(pixmap)
            self.expand_button.setVisible(False)
        else:
            self.content_label.setText(content)
            self.expand_button.setVisible(False)
    
    def handle_link(self, content):
        """处理链接内容"""
        self.content_label.setText(content)
        self.content_label.setTextFormat(Qt.RichText)
        self.expand_button.setVisible(False)
    
    def handle_html(self, content):
        """处理HTML内容"""
        self.content_label.setText(content)
        self.expand_button.setVisible(False)
    
    def handle_code(self, content):
        """处理代码内容，添加语法高亮"""
        # 存储完整内容
        self.full_content = content
        
        # 为确保滚动条显示，需要设置最小高度
        self.content_label.setMinimumHeight(200)
        
        # 如果内容太长，先显示部分内容
        if len(content) > 1000:
            truncated = content[:1000] + "..."
            self.truncated_content = truncated
            self.content_label.setText(self.format_code(truncated))
            self.expand_button.setVisible(True)
            self.expand_button.setText("展开全部")
            self.is_expanded = False
        else:
            self.content_label.setText(self.format_code(content))
            self.expand_button.setVisible(False)
            
        # 强制布局更新，确保内容尺寸正确计算
        self.content_container.adjustSize()
    
    def handle_long_text(self, content):
        """处理长文本内容"""
        # 存储完整内容
        self.full_content = content
        
        # 为确保滚动条显示，需要设置最小高度
        self.content_label.setMinimumHeight(200)
        
        # 如果内容太长，先显示部分内容
        if len(content) > 1000:
            truncated = content[:1000] + "..."
            self.truncated_content = truncated
            self.content_label.setText(truncated)
            self.expand_button.setVisible(True)
            self.expand_button.setText("展开全部")
            self.is_expanded = False
        else:
            self.content_label.setText(content)
            self.expand_button.setVisible(False)
            
        # 强制布局更新，确保内容尺寸正确计算
        self.content_container.adjustSize()
    
    def handle_text(self, content):
        """处理普通文本内容"""
        self.content_label.setText(content)
        self.expand_button.setVisible(False)
    
    def format_code(self, code):
        """格式化代码，添加语法高亮"""
        if not PYGMENTS_AVAILABLE:
            # 使用自定义字体的pre标签
            if StyleSheet.FONT_LOADED:
                return f'<pre style="font-family: \'{StyleSheet.FONT_FAMILY}\', Consolas, monospace;">{code}</pre>'
            else:
                return f"<pre>{code}</pre>"
            
        try:
            language = CodeDetector.detect_language(code)
            lexer = get_lexer_by_name(language, stripall=True)
            formatter = HtmlFormatter(style='monokai')
            highlighted_code = highlight(code, lexer, formatter)
            css = formatter.get_style_defs('.highlight')
            
            # 添加自定义字体到CSS
            if StyleSheet.FONT_LOADED:
                css += f"\n.highlight pre {{ font-family: '{StyleSheet.FONT_FAMILY}', Consolas, monospace; }}"
            
            return f"<style>{css}</style>{highlighted_code}"
        except:
            # 使用自定义字体的pre标签
            if StyleSheet.FONT_LOADED:
                return f'<pre style="font-family: \'{StyleSheet.FONT_FAMILY}\', Consolas, monospace;">{code}</pre>'
            else:
                return f"<pre>{code}</pre>"
    
    def toggle_expand(self):
        """切换展开/折叠状态"""
        if self.is_expanded:
            # 折叠
            if self.content_type == "文本" and CodeDetector.is_code(self.full_content):
                self.content_label.setText(self.format_code(self.truncated_content))
            else:
                self.content_label.setText(self.truncated_content)
            self.expand_button.setText("展开全部")
            self.is_expanded = False
        else:
            # 展开
            if self.content_type == "文本" and CodeDetector.is_code(self.full_content):
                self.content_label.setText(self.format_code(self.full_content))
            else:
                self.content_label.setText(self.full_content)
            self.expand_button.setText("折叠")
            self.is_expanded = True

class TitleBar(QWidget):
    """自定义标题栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.initUI()
        
    def initUI(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # 标题
        self.title_label = QLabel("剪贴板内容")
        self.title_label.setStyleSheet(StyleSheet.TITLE)
        
        # 类型标签
        self.type_label = QLabel("")
        self.type_label.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        
        # 添加到布局
        layout.addWidget(self.title_label)
        layout.addWidget(self.type_label)
        layout.addStretch(1)
        
        # 设置样式
        self.setStyleSheet(StyleSheet.TITLE_BAR)
    
    def set_title(self, title, content_type):
        """设置标题和内容类型"""
        self.title_label.setText(title)
        self.type_label.setText(f"({content_type})")
        
        # 针对不同类型设置颜色
        color = StyleSheet.TYPE_COLORS.get(content_type, "#e0e0e0")
        self.type_label.setStyleSheet(f"color: {color}; font-size: 13px;")

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
        central_widget.setStyleSheet(StyleSheet.MAIN_WINDOW)
        
        # 设置布局
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建标题栏
        self.title_bar = TitleBar(self)
        self.layout.addWidget(self.title_bar)
        
        # 创建内容区域
        content_container = QWidget()
        content_container.setStyleSheet(StyleSheet.CONTENT_AREA)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建内容显示窗口部件
        self.content_widget = ContentWidget(self)
        content_layout.addWidget(self.content_widget)
        
        # 添加内容区域到布局
        self.layout.addWidget(content_container)
        
        # 设置初始大小和限制
        self.setMinimumWidth(400)  # 增加默认宽度
        self.setMinimumHeight(150) # 增加默认高度
        self.setMaximumHeight(800) # 增加最大高度
        self.setMaximumWidth(700)  # 增加最大宽度
        
        # 设置初始透明度
        self.setWindowOpacity(0.0)
        
        # 应用基础样式
        self.setStyleSheet(StyleSheet.get_base_style())
    
    def update_content(self, content):
        """更新窗口内容"""
        if not content:
            return
            
        content_type = content.get("type", "未知")
        content_value = content.get("content", "")
        
        # 设置标题
        self.title_bar.set_title("剪贴板内容", content_type)
        
        # 设置内容
        self.content_widget.set_content(content_type, content_value)
        
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
                
                # 如果内容是字典而且包含raw_content字段，使用它
                if isinstance(content, dict) and "content" in content:
                    self.signals.update_preview.emit(content)
                    self.signals.show_preview.emit()
                else:
                    print(f"意外的剪贴板内容格式: {type(content)}")
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
