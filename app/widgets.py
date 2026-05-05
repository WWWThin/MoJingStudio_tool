# -*- coding: utf-8 -*-
"""
兼容层：把 app.widgets 映射到 app.ui.widgets
用于旧导入写法：
    from .widgets import *
"""

from .ui.widgets import *
