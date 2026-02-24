# utils/pagination.py
"""
分页工具
"""

import math
from typing import List, TypeVar, Generic

T = TypeVar('T')


class Paginator(Generic[T]):
    """分页器"""

    def __init__(self, items: List[T], page: int = 1, per_page: int = 10):
        """
        初始化分页器

        Args:
            items: 所有项目列表
            page: 当前页码（从 1 开始）
            per_page: 每页项目数
        """
        self.items = items
        self.page = max(1, page)
        self.per_page = per_page
        self.total = len(items)
        self.total_pages = math.ceil(self.total / self.per_page) if self.total > 0 else 1

    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages

    @property
    def prev_page(self) -> int:
        """上一页页码"""
        return max(1, self.page - 1)

    @property
    def next_page(self) -> int:
        """下一页页码"""
        return min(self.total_pages, self.page + 1)

    def get_page_items(self) -> List[T]:
        """获取当前页的项目"""
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        return self.items[start:end]

    def get_page_info(self) -> str:
        """获取页码信息字符串"""
        return f"{self.page}/{self.total_pages}"


def calculate_offset(page: int, per_page: int) -> int:
    """
    计算数据库查询的 offset

    Args:
        page: 页码（从 1 开始）
        per_page: 每页数量

    Returns:
        offset 值
    """
    return (max(1, page) - 1) * per_page


def calculate_total_pages(total_items: int, per_page: int) -> int:
    """
    计算总页数

    Args:
        total_items: 总项目数
        per_page: 每页数量

    Returns:
        总页数
    """
    return math.ceil(total_items / per_page) if total_items > 0 else 1
