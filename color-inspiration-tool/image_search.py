"""
图片搜索模块
Image Search Module

提供基于颜色和风格的本地图片搜索功能，包括：
- 从 CSV 加载图片元数据
- 使用 Lab 色彩空间和 Delta E 距离进行颜色匹配
- 按颜色或颜色+风格进行相似搜索

所有计算完全本地化，无需网络连接。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import warnings

# 色彩转换库
try:
    from colormath.color_objects import sRGBColor, LabColor
    from colormath.color_conversions import convert_color
    COLORMATH_AVAILABLE = True
except ImportError:
    COLORMATH_AVAILABLE = False
    warnings.warn(
        "colormath 库未安装。请运行: pip install colormath\n"
        "将使用简化版本的颜色距离计算。",
        ImportWarning
    )

# 可选：使用 KDTree 加速大规模搜索
try:
    from scipy.spatial import cKDTree
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ============= 全局变量 =============

# 图片数据缓存
_image_data_cache: Optional[pd.DataFrame] = None
_lab_values_cache: Optional[np.ndarray] = None
_kdtree_cache: Optional[object] = None


# ============= 颜色转换函数 =============

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    将 HEX 颜色转换为 RGB。
    
    Args:
        hex_color (str): HEX 颜色码，格式 '#RRGGBB'
        
    Returns:
        Tuple[int, int, int]: RGB 三元组，值在 0-255 范围内
    """
    hex_color = hex_color.lstrip('#').upper()
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    将 RGB 颜色转换为 Lab 色彩空间。
    
    如果 colormath 可用，使用标准的 sRGB to Lab 转换。
    否则使用简化的近似转换。
    
    Args:
        rgb (Tuple[int, int, int]): RGB 三元组，值在 0-255 范围内
        
    Returns:
        Tuple[float, float, float]: Lab 三元组
            - L: 亮度，范围 0-100
            - a: 绿-红通道，范围 -128 到 127
            - b: 蓝-黄通道，范围 -128 到 127
    """
    if COLORMATH_AVAILABLE:
        # 使用 colormath 进行精确转换
        rgb_color = sRGBColor(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
        lab_color = convert_color(rgb_color, LabColor)
        return (lab_color.lab_l, lab_color.lab_a, lab_color.lab_b)
    else:
        # 简化的 RGB -> Lab 转换（用于无 colormath 的情况）
        # 先转到 XYZ，再转到 Lab
        r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
        
        # gamma 校正
        r = r / 12.92 if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4
        
        # RGB -> XYZ
        x = r * 0.4124 + g * 0.3576 + b * 0.1805
        y = r * 0.2126 + g * 0.7152 + b * 0.0722
        z = r * 0.0193 + g * 0.1192 + b * 0.9505
        
        # 归一化
        x /= 0.95047
        y /= 1.00000
        z /= 1.08883
        
        # XYZ -> Lab
        epsilon = 0.008856
        kappa = 903.3
        
        fx = x ** (1/3) if x > epsilon else (kappa * x + 16) / 116
        fy = y ** (1/3) if y > epsilon else (kappa * y + 16) / 116
        fz = z ** (1/3) if z > epsilon else (kappa * z + 16) / 116
        
        L = 116 * fy - 16
        a = 500 * (fx - fy)
        b_val = 200 * (fy - fz)
        
        return (L, a, b_val)


def hex_to_lab(hex_color: str) -> Tuple[float, float, float]:
    """
    将 HEX 颜色直接转换为 Lab。
    
    Args:
        hex_color (str): HEX 颜色码
        
    Returns:
        Tuple[float, float, float]: Lab 三元组
    """
    rgb = hex_to_rgb(hex_color)
    return rgb_to_lab(rgb)


def delta_e_cie76(lab1: Tuple[float, float, float],
                  lab2: Tuple[float, float, float]) -> float:
    """
    计算两个 Lab 颜色之间的 Delta E (CIE76) 距离。
    
    Delta E CIE76 是最简单的色差公式：
    ΔE = sqrt((ΔL)² + (Δa)² + (Δb)²)
    
    一般来说：
    - ΔE < 1：人眼难以察觉差异
    - 1 < ΔE < 3：相似，但仔细看能感知
    - 3 < ΔE < 10：明显不同
    - ΔE > 10：非常不同
    
    Args:
        lab1 (Tuple[float, float, float]): 第一个 Lab 颜色
        lab2 (Tuple[float, float, float]): 第二个 Lab 颜色
        
    Returns:
        float: Delta E 距离（越小越接近）
        
    Example:
        >>> lab1 = (50, 10, 20)
        >>> lab2 = (52, 11, 19)
        >>> delta_e = delta_e_cie76(lab1, lab2)
        >>> delta_e
        2.3979...
    """
    dL = lab2[0] - lab1[0]
    da = lab2[1] - lab1[1]
    db = lab2[2] - lab1[2]
    return np.sqrt(dL**2 + da**2 + db**2)


# ============= 数据加载和缓存 =============

def load_image_data(csv_path: str = 'data/color_data.csv',
                    images_dir: str = 'data/images') -> pd.DataFrame:
    """
    加载图片元数据 CSV 文件，并预计算 Lab 值。
    
    期望 CSV 列：hex, object_name, style, image_path
    其中 image_path 是相对于 images_dir 的文件名。
    
    Args:
        csv_path (str): CSV 文件路径
        images_dir (str): 图片文件夹路径
        
    Returns:
        pd.DataFrame: 包含以下列的数据框：
            - hex: 颜色 HEX 码
            - object_name: 物体名称
            - style: 风格类别
            - image_path: 完整图片路径
            - L, a, b: Lab 色彩空间值
            - delta_e: 用于存储搜索结果的距离（初始为 NaN）
            
    Raises:
        FileNotFoundError: 如果 CSV 文件不存在
    """
    global _image_data_cache, _lab_values_cache, _kdtree_cache
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")
    
    # 加载 CSV
    df = pd.read_csv(csv_path)
    
    # 验证必需列
    required_cols = {'hex', 'object_name', 'style', 'image_path'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV 必须包含列: {required_cols}，实际列: {set(df.columns)}")
    
    # 构建完整的图片路径
    df['image_path'] = df['image_path'].apply(
        lambda x: str(Path(images_dir) / x)
    )
    
    # 计算 Lab 值
    lab_values = []
    for idx, row in df.iterrows():
        try:
            hex_color = row['hex']
            lab = hex_to_lab(hex_color)
            lab_values.append(lab)
        except Exception as e:
            warnings.warn(f"无法转换颜色 {row['hex']}（行 {idx}）: {e}")
            lab_values.append((np.nan, np.nan, np.nan))
    
    # 添加 Lab 列
    df[['L', 'a', 'b']] = pd.DataFrame(lab_values, index=df.index)
    
    # 添加距离列（用于搜索结果）
    df['delta_e'] = np.nan
    
    # 缓存数据
    _image_data_cache = df.copy()
    _lab_values_cache = np.array([[row['L'], row['a'], row['b']]
                                   for _, row in df.iterrows()])
    
    # 如果可用，预构建 KDTree（用于大规模搜索优化）
    if SCIPY_AVAILABLE and len(df) > 100:
        valid_mask = ~np.isnan(_lab_values_cache).any(axis=1)
        if valid_mask.sum() > 0:
            _kdtree_cache = cKDTree(_lab_values_cache[valid_mask])
    
    return df.copy()


def get_image_data() -> Optional[pd.DataFrame]:
    """
    获取缓存的图片数据。
    
    如果数据未加载，返回 None。
    
    Returns:
        Optional[pd.DataFrame]: 图片数据框，或 None
    """
    return _image_data_cache.copy() if _image_data_cache is not None else None


def clear_cache() -> None:
    """清空所有缓存数据。"""
    global _image_data_cache, _lab_values_cache, _kdtree_cache
    _image_data_cache = None
    _lab_values_cache = None
    _kdtree_cache = None


# ============= 搜索函数 =============

def search_by_color(hex_color: str,
                    top_n: int = 8,
                    data: Optional[pd.DataFrame] = None) -> List[Dict]:
    """
    按颜色进行相似搜索。
    
    输入 HEX 颜色，计算与数据集中所有图片的 Delta E 距离，
    返回最接近的前 top_n 条记录。
    
    Args:
        hex_color (str): 查询颜色的 HEX 码
        top_n (int): 返回的结果数量，默认 8
        data (Optional[pd.DataFrame]): 指定图片数据框。
                                       如果为 None，使用缓存数据。
        
    Returns:
        List[Dict]: 搜索结果列表，每项包含：
            - hex: 颜色
            - object_name: 物体名
            - style: 风格
            - image_path: 图片路径
            - delta_e: 与查询颜色的距离
            
            按 delta_e 升序排列。
            
    Raises:
        ValueError: 如果没有有效数据
        
    Example:
        >>> results = search_by_color('#FF0000', top_n=5)
        >>> print(results[0]['object_name'])
        'apple'
    """
    if data is None:
        data = _image_data_cache
    
    if data is None:
        raise ValueError("没有加载图片数据。请先调用 load_image_data()。")
    
    # 确保数据不为空
    if len(data) == 0:
        raise ValueError("图片数据为空。")
    
    # 转换查询颜色
    query_lab = hex_to_lab(hex_color)
    
    # 计算与所有颜色的距离
    distances = []
    for idx, row in data.iterrows():
        if pd.isna(row['L']) or pd.isna(row['a']) or pd.isna(row['b']):
            distances.append(float('inf'))
        else:
            dist = delta_e_cie76(query_lab, (row['L'], row['a'], row['b']))
            distances.append(dist)
    
    # 创建结果数据框
    result_data = data.copy()
    result_data['delta_e'] = distances
    
    # 排序并获取前 top_n
    result_data = result_data.dropna(subset=['L', 'a', 'b'])
    result_data = result_data.sort_values('delta_e').head(top_n)
    
    # 转换为结果字典列表
    results = []
    for _, row in result_data.iterrows():
        results.append({
            'hex': row['hex'],
            'object_name': row['object_name'],
            'style': row['style'],
            'image_path': row['image_path'],
            'delta_e': float(row['delta_e']),
        })
    
    return results


def search_by_style_and_color(hex_color: str,
                               style: str,
                               top_n: int = 5,
                               data: Optional[pd.DataFrame] = None) -> List[Dict]:
    """
    按颜色和风格进行相似搜索。
    
    先按风格筛选数据，再进行颜色相似搜索。
    
    Args:
        hex_color (str): 查询颜色的 HEX 码
        style (str): 风格类别，必须与 CSV 中的值匹配
        top_n (int): 返回的结果数量，默认 5
        data (Optional[pd.DataFrame]): 指定图片数据框。
                                       如果为 None，使用缓存数据。
        
    Returns:
        List[Dict]: 搜索结果列表，每项包含：
            - hex: 颜色
            - object_name: 物体名
            - style: 风格
            - image_path: 图片路径
            - delta_e: 与查询颜色的距离
            
            按 delta_e 升序排列。
            
    Raises:
        ValueError: 如果没有有效数据或指定风格不存在
        
    Example:
        >>> results = search_by_style_and_color('#FF0000', '卡通', top_n=3)
        >>> print(results[0]['object_name'])
    """
    if data is None:
        data = _image_data_cache
    
    if data is None:
        raise ValueError("没有加载图片数据。请先调用 load_image_data()。")
    
    # 按风格筛选
    filtered_data = data[data['style'] == style].copy()
    
    if len(filtered_data) == 0:
        raise ValueError(f"没有找到风格为 '{style}' 的图片。")
    
    # 使用 search_by_color 进行颜色搜索
    return search_by_color(hex_color, top_n=top_n, data=filtered_data)


# ============= 统计和信息函数 =============

def get_available_styles(data: Optional[pd.DataFrame] = None) -> List[str]:
    """
    获取数据中可用的所有风格。
    
    Args:
        data (Optional[pd.DataFrame]): 指定图片数据框。
                                       如果为 None，使用缓存数据。
        
    Returns:
        List[str]: 风格列表，已排序
        
    Example:
        >>> styles = get_available_styles()
        >>> print(styles)
        ['卡通', '水彩', '真实']
    """
    if data is None:
        data = _image_data_cache
    
    if data is None:
        return []
    
    return sorted(data['style'].unique().tolist())


def get_dataset_info(data: Optional[pd.DataFrame] = None) -> Dict:
    """
    获取数据集的统计信息。
    
    Args:
        data (Optional[pd.DataFrame]): 指定图片数据框。
                                       如果为 None，使用缓存数据。
        
    Returns:
        Dict: 包含以下键的统计信息：
            - total_images: 总图片数
            - valid_colors: 有效的颜色记录数
            - available_styles: 可用风格列表
            - style_counts: 各风格的图片数量
            
    Example:
        >>> info = get_dataset_info()
        >>> print(f"总共 {info['total_images']} 张图片")
    """
    if data is None:
        data = _image_data_cache
    
    if data is None:
        return {}
    
    valid_colors = (~data[['L', 'a', 'b']].isna().any(axis=1)).sum()
    
    return {
        'total_images': len(data),
        'valid_colors': valid_colors,
        'available_styles': get_available_styles(data),
        'style_counts': data['style'].value_counts().to_dict(),
    }


# ============= 使用示例和初始化 =============

if __name__ == '__main__':
    """
    模块使用示例
    """
    
    print("图片搜索模块示例")
    print("=" * 50)
    
    try:
        # 1. 加载数据
        print("\n1. 加载图片数据...")
        df = load_image_data('data/color_data.csv', 'data/images')
        print(f"   ✓ 加载了 {len(df)} 条记录")
        
        # 2. 获取数据集信息
        print("\n2. 数据集信息:")
        info = get_dataset_info(df)
        print(f"   - 总图片数: {info['total_images']}")
        print(f"   - 有效颜色: {info['valid_colors']}")
        print(f"   - 可用风格: {info['available_styles']}")
        
        # 3. 按颜色搜索
        print("\n3. 按颜色搜索 (#FF0000)...")
        results = search_by_color('#FF0000', top_n=3, data=df)
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['object_name']} ({result['style']}) "
                  f"- 距离: {result['delta_e']:.2f}")
        
        # 4. 按颜色和风格搜索
        print("\n4. 按颜色和风格搜索...")
        if info['available_styles']:
            style = info['available_styles'][0]
            try:
                results = search_by_style_and_color(
                    '#FF0000', style, top_n=2, data=df
                )
                print(f"   风格 '{style}' 中的相似颜色:")
                for i, result in enumerate(results, 1):
                    print(f"   {i}. {result['object_name']} "
                          f"- 距离: {result['delta_e']:.2f}")
            except ValueError as e:
                print(f"   (无结果: {e})")
        
    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        print("   请确保 'data/color_data.csv' 文件存在。")

