# bot/states.py
"""
FSM 状态定义
"""

from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    """上传合集状态"""
    waiting_for_media = State()       # 等待上传媒体
    waiting_for_name = State()        # 等待输入名称
    waiting_for_description = State() # 等待输入描述
    waiting_for_tags = State()        # 等待输入标签
    waiting_for_permission = State()  # 等待选择权限


class AddMediaStates(StatesGroup):
    """向现有合集添加媒体状态"""
    waiting_for_media = State()       # 等待上传媒体


class TransferTaskStates(StatesGroup):
    """搬运任务状态"""
    waiting_for_chat_id = State()     # 等待输入频道 ID
    waiting_for_filter_type = State() # 等待选择过滤类型
    waiting_for_keywords = State()    # 等待输入关键词
    waiting_for_task_name = State()   # 等待输入任务名称


class ApproveTaskStates(StatesGroup):
    """审核任务状态"""
    waiting_for_name = State()        # 等待输入合集名称
    waiting_for_description = State() # 等待输入描述
    waiting_for_tags = State()        # 等待输入标签
    waiting_for_permission = State()  # 等待选择权限


class AdminSettingsStates(StatesGroup):
    """管理员设置状态"""
    waiting_welcome_message = State()    # 等待输入欢迎消息
    waiting_welcome_buttons = State()    # 等待设置欢迎消息按钮
    waiting_broadcast_message = State()  # 等待输入广播消息
    waiting_broadcast_buttons = State()  # 等待设置广播消息按钮
    confirming_broadcast = State()       # 确认广播发送


class SearchStates(StatesGroup):
    """搜索状态"""
    waiting_for_keyword = State()        # 等待输入搜索关键词


class EditCollectionStates(StatesGroup):
    """编辑合集状态"""
    waiting_for_name = State()           # 等待输入新名称
    waiting_for_description = State()    # 等待输入新描述
    waiting_for_tags = State()           # 等待输入新标签
