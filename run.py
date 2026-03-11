#!/usr/bin/env python3
"""
FastAPI项目 - 启动脚本
启动A股短线选股AI系统的API服务
"""
import argparse
import uvicorn
import os
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_env():
    """设置环境变量"""
    # 设置环境
    os.environ.setdefault("ENV", "development")

    # 设置缓存目录
    os.environ.setdefault("CACHE_DIR", "./cache")

    logger.info(f"Environment: {os.getenv('ENV')}")
    logger.info(f"Cache directory: {os.getenv('CACHE_DIR')}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="A股短线选股AI系统 API服务")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口 (默认: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="启用自动重载 (开发模式)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数 (默认: 1, 生产环境建议设置)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认: info)"
    )
    parser.add_argument(
        "--env",
        type=str,
        default="development",
        choices=["development", "production"],
        help="运行环境 (默认: development)"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./cache",
        help="缓存目录 (默认: ./cache)"
    )

    args = parser.parse_args()

    # 设置环境变量
    os.environ["ENV"] = args.env
    os.environ["CACHE_DIR"] = args.cache_dir

    setup_env()

    # 打印启动信息
    logger.info("=" * 60)
    logger.info("🚀 A股短线选股AI系统 API服务启动中...")
    logger.info("=" * 60)
    logger.info(f"服务地址: http://{args.host}:{args.port}")
    logger.info(f"环境: {args.env}")
    logger.info(f"缓存目录: {args.cache_dir}")
    logger.info(f"自动重载: {'开启' if args.reload else '关闭'}")
    logger.info(f"工作进程: {args.workers}")
    logger.info(f"日志级别: {args.log_level}")
    logger.info("=" * 60)

    # 启动服务
    try:
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if args.env == "production" else 1,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 收到停止信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"服务启动失败: {e}", exc_info=True)
        raise
    finally:
        logger.info("✅ 服务已停止")


if __name__ == "__main__":
    main()