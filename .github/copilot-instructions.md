# ClipBoard Enhance 项目指南 - GitHub Copilot 指令

## 项目概述
ClipBoard Enhance 是一个运行在 Windows 上的应用程序，亦在为 Windows 实现增强的剪贴板体验。
基于 Python 技术栈开发，使用 PyQt5 构建预览窗口，pyperclip 用于监听与写入剪贴板，win11toast 用于实现通知。

## 代码规范
- 使用 Python 3.13.2 编写所有代码
- 遵循 PEP 8 代码风格规范
- 使用类型提示增强代码可读性
- 所有函数和类都应有reST风格的文档字符串(docstring)
- 项目的日志模块使用 log.py 并使用简体中文输出
- 尽量不要将代码写在 main.py 中，以便实现 Cython 的代码加速
- 尽可能写出弹性可扩展、可维护的代码

## 回复用户规则
- 当用户提出了产品的问题或者解决问题的思路时，应当在适时且随机的时候回答前肯定用户的想法
- 如 `你的理解非常到位，抓住了问题的核心`、`这个想法非常不错` 等等
- 每次鼓励尽可能用不同的词语和语法，但也不要次次都鼓励
- 除非用户明确说明需要你来实现相关功能，否则只给出思路，不要给出实现代码甚至直接为用户编辑

## 命名约定
- 类名: PascalCase
- 函数和变量: snake_case
- 常量: UPPER_SNAKE_CASE
- 文件名: snake_case.py
- 模块名: snake_case