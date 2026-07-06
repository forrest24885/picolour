"""
形状与配色模块
Shape and Color Module

提供形状识别和基于形状的调色板推荐功能，包括：
- 根据多边形顶点分类形状（圆形、方形、三角形、有机形）
- 基于形状类型推荐配色方案

所有计算完全本地化，无需网络连接。
"""

import numpy as np
from typing import List, Tuple, Literal, Dict
import warnings
import math

# 可选：使用 OpenCV 辅助（用于更精确的形状处理）
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# ============= 调色板定义 =============

# 预定义的调色板库，按形状和心情分类
COLOR_PALETTES = {
    '圆形': {
        'auto': ['#FFB7B2', '#E2F0CB', '#FFDAC1', '#B5EAD7'],  # 柔和粉彩
        'calm': ['#D5F4E6', '#A8E6CF', '#FFD3B6', '#FFAAA5'],    # 平静温柔
        'vibrant': ['#FF6B6B', '#FFA500', '#FFE66D', '#95E1D3'],  # 充满活力
        'dark': ['#2C3E50', '#34495E', '#7F8C8D', '#95A5A6'],     # 深色稳重
    },
    '方形': {
        'auto': ['#2B2D42', '#8D99AE', '#EDF2F4', '#EF233C'],    # 现代稳重
        'calm': ['#264653', '#2A9D8F', '#E9C46A', '#F4A261'],     # 冷静优雅
        'vibrant': ['#FF006E', '#FB5607', '#FFBE0B', '#8338EC'],  # 现代活力
        'dark': ['#1A1A2E', '#16213E', '#0F3460', '#E94560'],     # 深色对比
    },
    '三角形': {
        'auto': ['#F4A261', '#E76F51', '#E9C46A', '#264653'],     # 活力对比
        'calm': ['#F1A208', '#D5622B', '#6A4423', '#A0978C'],     # 暖调平静
        'vibrant': ['#FF006E', '#FFF000', '#03DAC6', '#CF6679'],  # 极致活力
        'dark': ['#003049', '#669BBC', '#F77F00', '#FCBF49'],     # 深色冒险
    },
    '有机形': {
        'auto': ['#FFC8DD', '#BDE0FE', '#A2D2FF', '#CDB4DB'],     # 梦幻流体
        'calm': ['#F8B4D4', '#F4A4D4', '#E8B4E8', '#D8B4E8'],     # 梦幻温柔
        'vibrant': ['#FF006E', '#FB5607', '#FFBE0B', '#8338EC'],  # 梦幻活力
        'dark': ['#6A3E37', '#8B4513', '#A0826D', '#C4A37B'],     # 深色流体
    },
    'unknown': {
        'auto': ['#3498DB', '#2ECC71', '#E74C3C', '#F39C12'],     # 通用配色
        'calm': ['#BDC3C7', '#95A5A6', '#7F8C8D', '#34495E'],     # 通用平静
        'vibrant': ['#E91E63', '#2196F3', '#4CAF50', '#FF5722'],  # 通用活力
        'dark': ['#212121', '#424242', '#616161', '#9E9E9E'],     # 通用深色
    }
}


# ============= 几何计算函数 =============

def calculate_polygon_area(points: List[Tuple[float, float]]) -> float:
    """
    计算多边形面积（使用 Shoelace 公式）。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表 [(x1,y1), (x2,y2), ...]
        
    Returns:
        float: 多边形面积
        
    Example:
        >>> area = calculate_polygon_area([(0,0), (1,0), (1,1), (0,1)])
        >>> area
        1.0
    """
    if len(points) < 3:
        return 0.0
    
    points = np.array(points, dtype=np.float64)
    x = points[:, 0]
    y = points[:, 1]
    
    # Shoelace 公式
    return abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])) / 2.0


def calculate_convex_hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    计算多边形的凸包。
    
    使用 Graham 扫描算法或 OpenCV（如果可用）。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        List[Tuple[float, float]]: 凸包顶点列表
    """
    if CV2_AVAILABLE:
        # 使用 OpenCV 计算凸包
        points_array = np.array(points, dtype=np.float32)
        hull = cv2.convexHull(points_array)
        return [(float(p[0][0]), float(p[0][1])) for p in hull]
    else:
        # 手动实现 Graham 扫描（简化版）
        return _graham_scan(points)


def _graham_scan(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Graham 扫描算法计算凸包（简化实现）。
    
    Args:
        points (List[Tuple[float, float]]): 点列表
        
    Returns:
        List[Tuple[float, float]]: 凸包顶点
    """
    def cross(o: Tuple, a: Tuple, b: Tuple) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    
    points = sorted(set(points))
    if len(points) <= 1:
        return points
    
    # 构建下凸包
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    
    # 构建上凸包
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    
    return lower[:-1] + upper[:-1]


def calculate_convex_hull_area(points: List[Tuple[float, float]]) -> float:
    """
    计算凸包面积。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        float: 凸包面积
    """
    hull = calculate_convex_hull(points)
    return calculate_polygon_area(hull)


def calculate_convexity_ratio(points: List[Tuple[float, float]]) -> float:
    """
    计算凸性比（凸包面积 / 多边形面积）。
    
    接近 1 表示凸多边形，< 1 表示有凹陷。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        float: 凸性比，范围 0-1
    """
    poly_area = calculate_polygon_area(points)
    if poly_area == 0:
        return 0.0
    
    hull_area = calculate_convex_hull_area(points)
    return hull_area / poly_area


def get_centroid(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    计算多边形的质心。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        Tuple[float, float]: 质心坐标 (x, y)
    """
    points_array = np.array(points, dtype=np.float64)
    return (float(np.mean(points_array[:, 0])), float(np.mean(points_array[:, 1])))


def calculate_circularity(points: List[Tuple[float, float]]) -> float:
    """
    计算圆形度（离心率）。
    
    计算所有顶点到质心的距离，然后计算距离的标准差。
    低值表示更接近圆形。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        float: 圆形度（标准差），值越小越圆
    """
    if len(points) < 3:
        return float('inf')
    
    centroid = get_centroid(points)
    distances = [
        math.sqrt((p[0] - centroid[0])**2 + (p[1] - centroid[1])**2)
        for p in points
    ]
    
    mean_dist = np.mean(distances)
    if mean_dist == 0:
        return 0.0
    
    std_dist = np.std(distances)
    return std_dist / mean_dist  # 归一化的标准差


def get_minimum_bounding_rectangle(points: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    """
    计算最小外接矩形的长宽比。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        Tuple[float, float, float]: (长, 宽, 长宽比)
    """
    if CV2_AVAILABLE:
        points_array = np.array(points, dtype=np.float32)
        rect = cv2.minAreaRect(points_array)
        width, height = rect[1]
        width, height = max(width, height), min(width, height)
        ratio = width / height if height != 0 else float('inf')
        return (width, height, ratio)
    else:
        # 简化实现：使用 axis-aligned 矩形
        points_array = np.array(points)
        x_min, x_max = np.min(points_array[:, 0]), np.max(points_array[:, 0])
        y_min, y_max = np.min(points_array[:, 1]), np.max(points_array[:, 1])
        width = x_max - x_min
        height = y_max - y_min
        ratio = max(width, height) / min(width, height) if min(width, height) != 0 else float('inf')
        return (max(width, height), min(width, height), ratio)


def count_vertices(points: List[Tuple[float, float]]) -> int:
    """
    计算多边形顶点数。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        int: 顶点数
    """
    return len(points)


# ============= 形状分类函数 =============

def classify_shape(points: List[Tuple[float, float]]) -> Literal['圆形', '方形', '三角形', '有机形']:
    """
    根据多边形顶点分类形状。
    
    使用启发式方法：
    - 圆形：顶点多（>=6）、圆形度低、凸性比高
    - 方形：顶点少（4）、长宽比接近 1、凸性比高
    - 三角形：顶点数 = 3
    - 有机形：其他情况
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表 [(x1,y1), (x2,y2), ...]
                                            至少需要 3 个点。
        
    Returns:
        Literal['圆形', '方形', '三角形', '有机形']: 分类结果
        
    Raises:
        ValueError: 如果顶点数少于 3
        
    Example:
        >>> # 正方形
        >>> points_square = [(0,0), (10,0), (10,10), (0,10)]
        >>> classify_shape(points_square)
        '方形'
        
        >>> # 正三角形
        >>> points_triangle = [(0,0), (10,0), (5,8.66)]
        >>> classify_shape(points_triangle)
        '三角形'
        
        >>> # 圆形
        >>> import math
        >>> points_circle = [(5 + 5*math.cos(2*math.pi*i/12), 5 + 5*math.sin(2*math.pi*i/12))
        ...                  for i in range(12)]
        >>> classify_shape(points_circle)
        '圆形'
    """
    if len(points) < 3:
        raise ValueError(f"顶点数必须至少为 3，得到: {len(points)}")
    
    # 计算特征
    num_vertices = count_vertices(points)
    convexity_ratio = calculate_convexity_ratio(points)
    circularity = calculate_circularity(points)
    width, height, bbox_ratio = get_minimum_bounding_rectangle(points)
    
    # 分类逻辑
    
    # 1. 首先检查三角形
    if num_vertices == 3:
        return '三角形'
    
    # 2. 检查方形
    # 特征：4个顶点，凸性高，长宽比接近 1
    if 3 <= num_vertices <= 5 and bbox_ratio < 1.5 and convexity_ratio > 0.8:
        return '方形'
    
    # 3. 检查圆形
    # 特征：顶点多，圆形度低，凸性高
    if num_vertices >= 6 and circularity < 0.3 and convexity_ratio > 0.85:
        return '圆形'
    
    # 4. 默认为有机形
    return '有机形'


# ============= 调色板推荐函数 =============

def recommend_palettes(
    shape_type: Literal['圆形', '方形', '三角形', '有机形'],
    mood: Literal['auto', 'calm', 'vibrant', 'dark'] = 'auto'
) -> List[str]:
    """
    根据形状类型和心情返回推荐的调色板。
    
    Args:
        shape_type (Literal): 形状类型，可选值：'圆形', '方形', '三角形', '有机形'
        mood (Literal): 心情/风格，可选值：
            - 'auto': 自动选择（默认）
            - 'calm': 平静、温柔的调色板
            - 'vibrant': 充满活力的调色板
            - 'dark': 深色、成熟的调色板
        
    Returns:
        List[str]: HEX 颜色码列表，通常包含 4 个颜色
        
    Raises:
        ValueError: 如果 shape_type 或 mood 不合法
        
    Example:
        >>> # 圆形 + 自动风格
        >>> palette = recommend_palettes('圆形')
        >>> len(palette)
        4
        >>> palette
        ['#FFB7B2', '#E2F0CB', '#FFDAC1', '#B5EAD7']
        
        >>> # 方形 + 活力风格
        >>> palette = recommend_palettes('方形', mood='vibrant')
        >>> palette
        ['#FF006E', '#FB5607', '#FFBE0B', '#8338EC']
    """
    # 验证参数
    valid_shapes = {'圆形', '方形', '三角形', '有机形', 'unknown'}
    valid_moods = {'auto', 'calm', 'vibrant', 'dark'}
    
    if shape_type not in valid_shapes:
        warnings.warn(
            f"未知的形状类型: {shape_type}。使用默认值 'unknown'。"
            f"有效值: {valid_shapes}"
        )
        shape_type = 'unknown'
    
    if mood not in valid_moods:
        warnings.warn(
            f"未知的心情: {mood}。使用默认值 'auto'。"
            f"有效值: {valid_moods}"
        )
        mood = 'auto'
    
    # 获取调色板
    if shape_type in COLOR_PALETTES:
        palette_dict = COLOR_PALETTES[shape_type]
        if mood in palette_dict:
            return palette_dict[mood].copy()
        else:
            return palette_dict['auto'].copy()
    
    return COLOR_PALETTES['unknown']['auto'].copy()


def get_all_palettes() -> Dict:
    """
    获取所有预定义的调色板。
    
    Returns:
        Dict: 调色板字典结构：
            {
                '形状1': {
                    '心情1': [颜色列表],
                    ...
                },
                ...
            }
    """
    return {k: v.copy() for k, v in COLOR_PALETTES.items()}


# ============= 组合函数 =============

def classify_and_get_palette(
    points: List[Tuple[float, float]],
    mood: Literal['auto', 'calm', 'vibrant', 'dark'] = 'auto'
) -> Tuple[Literal['圆形', '方形', '三角形', '有机形'], List[str]]:
    """
    一步完成：分类形状并获取对应的调色板。
    
    这是一个方便函数，结合了 classify_shape 和 recommend_palettes。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        mood (Literal): 心情/风格，默认 'auto'
        
    Returns:
        Tuple[str, List[str]]: (形状类型, 推荐调色板)
        
    Example:
        >>> points = [(0,0), (10,0), (10,10), (0,10)]
        >>> shape, palette = classify_and_get_palette(points)
        >>> print(f"形状: {shape}")
        形状: 方形
        >>> print(f"调色板: {palette}")
        调色板: ['#2B2D42', '#8D99AE', '#EDF2F4', '#EF233C']
    """
    shape_type = classify_shape(points)
    palette = recommend_palettes(shape_type, mood=mood)
    return shape_type, palette


# ============= 形状分析辅助函数 =============

def analyze_shape(points: List[Tuple[float, float]]) -> Dict:
    """
    进行详细的形状分析，返回所有特征。
    
    用于调试和了解形状特征。
    
    Args:
        points (List[Tuple[float, float]]): 多边形顶点列表
        
    Returns:
        Dict: 分析结果，包含：
            - num_vertices: 顶点数
            - area: 多边形面积
            - convexity_ratio: 凸性比
            - circularity: 圆形度
            - bbox_ratio: 外接矩形长宽比
            - centroid: 质心
            - classified_shape: 分类结果
            
    Example:
        >>> points = [(0,0), (10,0), (5,8.66)]
        >>> analysis = analyze_shape(points)
        >>> analysis['classified_shape']
        '三角形'
    """
    num_vertices = count_vertices(points)
    area = calculate_polygon_area(points)
    convexity_ratio = calculate_convexity_ratio(points)
    circularity = calculate_circularity(points)
    bbox_width, bbox_height, bbox_ratio = get_minimum_bounding_rectangle(points)
    centroid = get_centroid(points)
    classified = classify_shape(points)
    
    return {
        'num_vertices': num_vertices,
        'area': area,
        'convexity_ratio': convexity_ratio,
        'circularity': circularity,
        'bbox_width': bbox_width,
        'bbox_height': bbox_height,
        'bbox_ratio': bbox_ratio,
        'centroid': centroid,
        'classified_shape': classified,
    }


# ============= 使用示例 =============

if __name__ == '__main__':
    """
    模块使用示例
    """
    import math
    
    print("形状与配色模块示例")
    print("=" * 60)
    
    # 1. 测试形状分类
    print("\n1. 形状分类测试:")
    print("-" * 60)
    
    # 正方形
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    shape = classify_shape(square)
    print(f"正方形: {shape}")
    
    # 三角形
    triangle = [(0, 0), (10, 0), (5, 8.66)]
    shape = classify_shape(triangle)
    print(f"三角形: {shape}")
    
    # 圆形（12 边多边形逼近圆）
    circle = [
        (5 + 5 * math.cos(2 * math.pi * i / 12),
         5 + 5 * math.sin(2 * math.pi * i / 12))
        for i in range(12)
    ]
    shape = classify_shape(circle)
    print(f"圆形: {shape}")
    
    # 有机形
    organic = [(0, 0), (5, 1), (8, 3), (9, 7), (7, 9), (3, 10), (1, 8), (0, 5)]
    shape = classify_shape(organic)
    print(f"有机形: {shape}")
    
    # 2. 测试调色板推荐
    print("\n2. 调色板推荐测试:")
    print("-" * 60)
    
    shapes = ['圆形', '方形', '三角形', '有机形']
    moods = ['auto', 'calm', 'vibrant', 'dark']
    
    for s in shapes:
        print(f"\n{s}:")
        for m in moods:
            palette = recommend_palettes(s, mood=m)
            print(f"  {m:8s}: {palette}")
    
    # 3. 测试组合函数
    print("\n3. 组合函数测试:")
    print("-" * 60)
    
    shape, palette = classify_and_get_palette(square)
    print(f"正方形分类: {shape}")
    print(f"推荐调色板: {palette}")
    
    # 4. 测试详细分析
    print("\n4. 详细形状分析:")
    print("-" * 60)
    
    analysis = analyze_shape(square)
    for key, value in analysis.items():
        if isinstance(value, float):
            print(f"  {key:18s}: {value:.4f}")
        else:
            print(f"  {key:18s}: {value}")
