import log, sys
import platform

log.debug('检测系统类型...')
# 检查操作系统类型
if platform.system() != "Windows":
    log.error("这个程序仅适用于Windows系统。")
    sys.exit(1)

# 在主程序开始处添加更多日志
log.debug(f"系统参数: {sys.argv}")

log.debug('添加参数读取...')
import argparse
parser = argparse.ArgumentParser(description='Clipboard Enhance')
# 给这个解析对象添加命令行参数
parser.add_argument('-url', type=str, help='网盘链接')
parser.add_argument('-pwd', type=str, help='提取码')
parser.add_argument('--register', action='store_true', help='[ 需要管理员权限 ] 注册 netdisk:// 协议')

# 尝试过滤掉PyInstaller可能添加的额外参数
filtered_args = []
i = 0
while i < len(sys.argv):
    arg = sys.argv[i]
    if arg == '-url' and i+1 < len(sys.argv):
        filtered_args.append(arg)
        filtered_args.append(sys.argv[i+1])
        i += 2
    elif arg == '-pwd' and i+1 < len(sys.argv):
        filtered_args.append(arg)
        filtered_args.append(sys.argv[i+1])
        i += 2
    elif arg == '--register':
        filtered_args.append(arg)
        i += 1
    elif i > 0 and arg.endswith('.pyc'):
        # 跳过PyInstaller临时文件参数
        i += 1
    else:
        filtered_args.append(arg)
        i += 1

log.debug(f"过滤后参数: {filtered_args}")
args = parser.parse_args(filtered_args[1:] if len(filtered_args) > 1 else [])

args = parser.parse_args()

log.debug('启动主程序...')
from func import (
    exit_application, 
    handle_netdisk_protocol, 
    main
)

if __name__ == "__main__":
    try:
        # 检查命令行参数
        if args.pwd and not args.url:
            log.error("提取码需要与网盘链接一起提供。")
            sys.exit(1)
        if args.url or args.register:
            # 作为协议处理器运行
            log.debug(f'作为协议处理器运行，参数：\n- URL：{args.url}\n- 提取码：{args.pwd}\n- 注册：{args.register}')
            # 添加调试代码，显示接收到的完整参数
            log.debug(f"完整命令行: {sys.argv}")
            handle_netdisk_protocol(
                url=args.url,
                pwd=args.pwd,
                register=args.register
            )
            exit_application()
        else:
            main()
    except Exception:
        import traceback
        log.error(f'程序发生错误！\n{traceback.format_exc()}')
        input()