#!/usr/bin/env python3
"""
🔢 字节数转换为人类可读格式的工具
将字节数转换为 KB/MB/GB/TB 格式
"""

import math
import sys


def pretty_size(bytes_size):
    """
    将字节数转换为人类可读的格式

    Args:
        bytes_size (int): 字节数

    Returns:
        str: 格式化的大小字符串
    """
    if bytes_size == 0:
        return "0B"

    # 定义单位
    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    # 计算合适的单位
    unit_index = min(int(math.floor(math.log(bytes_size, 1024))), len(units) - 1)

    # 计算大小
    size = bytes_size / (1024**unit_index)

    # 格式化输出
    if unit_index == 0:
        return f"{int(size)}{units[unit_index]}"
    elif size >= 100:
        return f"{size:.0f}{units[unit_index]}"
    elif size >= 10:
        return f"{size:.1f}{units[unit_index]}"
    else:
        return f"{size:.2f}{units[unit_index]}"


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("Usage: python3 pretty_size.py <bytes>", file=sys.stderr)
        print("Example: python3 pretty_size.py 1048576", file=sys.stderr)
        sys.exit(1)

    try:
        bytes_size = int(sys.argv[1])
        if bytes_size < 0:
            raise ValueError("Size cannot be negative")

        result = pretty_size(bytes_size)
        print(result)

    except ValueError as e:
        print(f"Error: Invalid input - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
