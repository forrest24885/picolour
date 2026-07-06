"""
色彩计算工具模块
Color Utilities Module

提供纯函数式的颜色计算功能，包括：
- 色彩空间转换（HEX <-> RGB <-> HSV）
- 色彩和谐配置生成（互补色、分裂互补、三角色、相似色）
- 颜色渐变插值

所有功能基于 Python 标准库 colorsys，不依赖任何网络服务。
"""

import colorsys
from typing import Tuple, List


# ============= 基础色彩转换函数 =============

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    将 HEX 颜色转换为 RGB 三元组。
    
    Args:
        hex_color (str): 16 进制颜色码，格式为 '#RRGGBB'（大小写均可）
        
    Returns:
        Tuple[int, int, int]: RGB 三元组，每个值在 0-255 范围内
        
    Raises:
        ValueError: 如果颜色格式不合法
        
    Example:
        >>> hex_to_rgb('#FF5733')
        (255, 87, 51)
        >>> hex_to_rgb('FF5733')  # 不带 # 也支持
        (255, 87, 51)
    """
    hex_color = hex_color.lstrip('#').upper()
    
    if len(hex_color) != 6 or not all(c in '0123456789ABCDEF' for c in hex_color):
        raise ValueError(f"无效的 HEX 颜色格式: {hex_color}。应为 '#RRGGBB' 格式。")
    
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    将 RGB 三元组转换为 HEX 颜色码。
    
    Args:
        rgb (Tuple[int, int, int]): RGB 三元组，每个值在 0-255 范围内
        
    Returns:
        str: 16 进制颜色码，格式为 '#RRGGBB'（大写）
        
    Raises:
        ValueError: 如果 RGB 值超出 0-255 范围
        
    Example:
        >>> rgb_to_hex((255, 87, 51))
        '#FF5733'
    """
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise ValueError(f"RGB 值必须在 0-255 范围内，得到: ({r}, {g}, {b})")
    
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    将 RGB 颜色转换为 HSV 色彩空间。
    
    Args:
        rgb (Tuple[int, int, int]): RGB 三元组，每个值在 0-255 范围内
        
    Returns:
        Tuple[float, float, float]: HSV 三元组，其中：
            - H (色调): 0.0-1.0，代表 0°-360°
            - S (饱和度): 0.0-1.0
            - V (明度): 0.0-1.0
            
    Example:
        >>> h, s, v = rgb_to_hsv((255, 87, 51))
        >>> int(h * 360), int(s * 100), int(v * 100)
        (11, 80, 100)
    """
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    return colorsys.rgb_to_hsv(r, g, b)


def hsv_to_rgb(hsv: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """
    将 HSV 色彩空间转换为 RGB 颜色。
    
    Args:
        hsv (Tuple[float, float, float]): HSV 三元组，其中：
            - H: 0.0-1.0（代表 0°-360°）
            - S: 0.0-1.0
            - V: 0.0-1.0
            
    Returns:
        Tuple[int, int, int]: RGB 三元组，每个值在 0-255 范围内
        
    Example:
        >>> rgb = hsv_to_rgb((0.0306, 0.8, 1.0))
        >>> rgb
        (255, 87, 51)
    """
    h, s, v = hsv[0], hsv[1], hsv[2]
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


# ============= 色彩和谐配置函数 =============

def get_complementary_color(hex_color: str) -> str:
    """
    获取补色（对比色）。
    
    原理：在 HSV 色彩空间中，互补色为色调相差 180 度（0.5）。
    
    Args:
        hex_color (str): 16 进制颜色码
        
    Returns:
        str: 互补色的 16 进制颜色码
        
    Example:
        >>> get_complementary_color('#FF5733')  # 橙红色的互补色
        '#3373FF'  # 蓝色
    """
    rgb = hex_to_rgb(hex_color)
    h, s, v = rgb_to_hsv(rgb)
    
    # 色调旋转 180 度（0.5）
    h_comp = (h + 0.5) % 1.0
    
    rgb_comp = hsv_to_rgb((h_comp, s, v))
    return rgb_to_hex(rgb_comp)


def get_split_complementary_colors(hex_color: str) -> List[str]:
    """
    获取分裂互补色配置。
    
    原理：在色相环上，选择互补色左右各 30 度（±1/12）的颜色，
    共返回包括原色在内的 3 个颜色。
    
    Args:
        hex_color (str): 16 进制颜色码
        
    Returns:
        List[str]: 包含 3 个颜色（原色、左补色、右补色）的 16 进制列表
        
    Example:
        >>> colors = get_split_complementary_colors('#FF0000')
        >>> len(colors)
        3
    """
    rgb = hex_to_rgb(hex_color)
    h, s, v = rgb_to_hsv(rgb)
    
    # 计算三个色调：原色、补色左偏 30°、补色右偏 30°
    h_comp_base = (h + 0.5) % 1.0
    h1 = h_comp_base - (30 / 360)  # 左偏 30°
    h2 = h_comp_base + (30 / 360)  # 右偏 30°
    
    # 归一化到 [0, 1)
    h1 = h1 % 1.0
    h2 = h2 % 1.0
    
    rgb1 = hsv_to_rgb((h1, s, v))
    rgb2 = hsv_to_rgb((h2, s, v))
    
    return [rgb_to_hex(rgb1), rgb_to_hex(rgb2)]


def get_triadic_colors(hex_color: str) -> List[str]:
    """
    获取三角色（三色和谐配置）。
    
    原理：在色相环上均匀分布三个颜色，每两个颜色之间相差 120 度（1/3）。
    共返回 3 个颜色（原色本身 + 另外两个三角色）。
    
    Args:
        hex_color (str): 16 进制颜色码
        
    Returns:
        List[str]: 包含 3 个 16 进制颜色码的列表（按色相顺序）
        
    Example:
        >>> colors = get_triadic_colors('#FF0000')  # 红色
        >>> len(colors)
        3
        >>> # 结果包括红色及其三角色（绿和蓝）
    """
    rgb = hex_to_rgb(hex_color)
    h, s, v = rgb_to_hsv(rgb)
    
    h1 = h
    h2 = (h + 1/3) % 1.0
    h3 = (h + 2/3) % 1.0
    
    rgb1 = hsv_to_rgb((h1, s, v))
    rgb2 = hsv_to_rgb((h2, s, v))
    rgb3 = hsv_to_rgb((h3, s, v))
    
    return [rgb_to_hex(rgb1), rgb_to_hex(rgb2), rgb_to_hex(rgb3)]


def get_analogous_colors(hex_color: str) -> List[str]:
    """
    获取相似色（相邻色配置）。
    
    原理：在色相环上选择原色及其左右各 30 度的颜色，
    共返回包括原色在内的 3 个相邻颜色。
    
    Args:
        hex_color (str): 16 进制颜色码
        
    Returns:
        List[str]: 包含 3 个相邻颜色的 16 进制列表
        
    Example:
        >>> colors = get_analogous_colors('#FF5733')
        >>> len(colors)
        3
    """
    rgb = hex_to_rgb(hex_color)
    h, s, v = rgb_to_hsv(rgb)
    
    # 原色及左右各 30° 的颜色
    h_left = (h - 30 / 360) % 1.0
    h_center = h
    h_right = (h + 30 / 360) % 1.0
    
    rgb_left = hsv_to_rgb((h_left, s, v))
    rgb_center = hsv_to_rgb((h_center, s, v))
    rgb_right = hsv_to_rgb((h_right, s, v))
    
    return [rgb_to_hex(rgb_left), rgb_to_hex(rgb_center), rgb_to_hex(rgb_right)]


# ============= 颜色插值函数 =============

def get_gradient(hex_color1: str, hex_color2: str, steps: int = 5) -> List[str]:
    """
    在两个颜色之间生成渐变色列表。
    
    原理：在 RGB 色彩空间中，对每个通道进行线性插值。
    
    Args:
        hex_color1 (str): 起始颜色的 16 进制码
        hex_color2 (str): 终止颜色的 16 进制码
        steps (int): 渐变步数，包括起始和终止颜色。默认值为 5。
                     最小值为 2（仅包括起始和终止颜色）。
        
    Returns:
        List[str]: 包含 steps 个 16 进制颜色码的列表
        
    Raises:
        ValueError: 如果 steps < 2
        
    Example:
        >>> colors = get_gradient('#FF0000', '#0000FF', steps=5)
        >>> len(colors)
        5
        >>> colors[0]
        '#FF0000'
        >>> colors[-1]
        '#0000FF'
    """
    if steps < 2:
        raise ValueError(f"步数必须至少为 2，得到: {steps}")
    
    rgb1 = hex_to_rgb(hex_color1)
    rgb2 = hex_to_rgb(hex_color2)
    
    gradient = []
    for i in range(steps):
        # 计算插值比例 [0, 1]
        ratio = i / (steps - 1) if steps > 1 else 0
        
        # 对每个通道进行线性插值
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
        
        gradient.append(rgb_to_hex((r, g, b)))
    
    return gradient


# ============= 快捷函数：获取所有和谐配置 =============

def get_all_harmonies(hex_color: str) -> dict:
    """
    获取指定颜色的所有和谐配置（一次性计算）。
    
    包括互补色、分裂互补、三角色、相似色等。
    
    Args:
        hex_color (str): 16 进制颜色码
        
    Returns:
        dict: 包含以下键的字典：
            - 'original': 原始颜色
            - 'complementary': 互补色（1 个）
            - 'split_complementary': 分裂互补色（2 个）
            - 'triadic': 三角色（3 个）
            - 'analogous': 相似色（3 个）
            
    Example:
        >>> harmonies = get_all_harmonies('#FF5733')
        >>> harmonies['complementary']
        '#3373FF'
    """
    return {
        'original': hex_color,
        'complementary': get_complementary_color(hex_color),
        'split_complementary': get_split_complementary_colors(hex_color),
        'triadic': get_triadic_colors(hex_color),
        'analogous': get_analogous_colors(hex_color),
    }
