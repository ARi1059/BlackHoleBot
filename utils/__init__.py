# utils/__init__.py
"""
工具函数模块
"""

from .deep_link import (
    generate_deep_link_code,
    generate_unique_deep_link_code,
    parse_start_parameter,
    create_deep_link,
)
from .pagination import (
    Paginator,
    calculate_offset,
    calculate_total_pages,
)

__all__ = [
    "generate_deep_link_code",
    "generate_unique_deep_link_code",
    "parse_start_parameter",
    "create_deep_link",
    "Paginator",
    "calculate_offset",
    "calculate_total_pages",
]
