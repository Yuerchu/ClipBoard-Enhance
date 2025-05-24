import log, sys
import platform
import time

log.debug('应用程序启动...')
log.debug('检测系统类型...')

# 检查操作系统类型
if platform.system() != "Windows":
    log.error("这个程序仅适用于Windows系统。")
    sys.exit(1)

log.debug(f"Python版本: {sys.version}")
log.debug(f"系统参数: {sys.argv}")

log.debug('初始化参数解析器...')
import argparse

try:
    parser = argparse.ArgumentParser(description='Clipboard Enhance - 增强的剪贴板工具')
    parser.add_argument('-url', type=str, help='网盘链接')
    parser.add_argument('-pwd', type=str, help='提取码')
    parser.add_argument('--register', action='store_true', help='[ 需要管理员权限 ] 注册 netdisk:// 协议')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--preview-delay', type=float, help='设置预览延迟时间（秒）')

    # 尝试过滤掉PyInstaller可能添加的额外参数
    filtered_args = []
    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['-url', '-pwd', '--preview-delay'] and i+1 < len(sys.argv):
            filtered_args.append(arg)
            filtered_args.append(sys.argv[i+1])
            i += 2
        elif arg in ['--register', '--debug']:
            filtered_args.append(arg)
            i += 1
        elif i > 0 and (arg.endswith('.pyc') or 'python' in arg.lower()):
            # 跳过Python相关的临时参数
            i += 1
        else:
            filtered_args.append(arg)
            i += 1

    log.debug(f"过滤后参数: {filtered_args}")
    args = parser.parse_args(filtered_args[1:] if len(filtered_args) > 1 else [])
    
    # 如果启用调试模式，设置更详细的日志级别
    if args.debug:
        log.set_debug_mode(True)
        log.debug('调试模式已启用')

except Exception as e:
    log.error(f'参数解析失败: {e}')
    sys.exit(1)

log.debug('导入主要模块...')
try:
    from func import (
        exit_application, 
        handle_netdisk_protocol, 
        main,
        config,
        save_config
    )
except Exception as e:
    log.error(f'导入模块失败: {e}')
    sys.exit(1)

if __name__ == "__main__":
    start_time = time.time()
    
    try:
        # 应用命令行预览延迟设置
        if args.preview_delay:
            if 0.1 <= args.preview_delay <= 2.0:
                config["preview_delay"] = args.preview_delay
                save_config()
                log.debug(f'预览延迟设置为: {args.preview_delay}秒')
            else:
                log.warning(f'无效的预览延迟时间: {args.preview_delay}，使用默认值')
        
        # 检查命令行参数
        if args.pwd and not args.url:
            log.error("提取码需要与网盘链接一起提供。")
            sys.exit(1)
            
        if args.url or args.register:
            # 作为协议处理器运行
            log.debug(f'作为协议处理器运行')
            log.debug(f'参数详情：\n- URL：{args.url}\n- 提取码：{args.pwd}\n- 注册：{args.register}')
            log.debug(f"完整命令行: {sys.argv}")
            
            handle_netdisk_protocol(
                url=args.url,
                pwd=args.pwd,
                register=args.register
            )
            exit_application()
        else:
            # 作为主程序运行
            log.debug('作为主程序运行')
            startup_time = time.time() - start_time
            log.debug(f'启动准备耗时: {startup_time:.3f}秒')
            
            main()
            
    except KeyboardInterrupt:
        log.debug('用户中断程序')
        sys.exit(0)
    except SystemExit:
        # 正常退出
        pass
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        log.error(f'程序发生未处理的错误:\n{error_msg}')
        
        # 尝试显示错误通知
        try:
            from func import toast
            toast('程序错误', f'发生未预期的错误: {str(e)}')
        except:
            pass
        
        # 在调试模式下等待用户输入
        if args.debug:
            input('按回车键退出...')
        
        sys.exit(1)