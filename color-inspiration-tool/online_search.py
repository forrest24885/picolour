"""
在线搜索模块
Online Search Module

提供从 Unsplash API 获取网络图片的功能。

依赖：
- requests: HTTP 请求库
- 环境变量 UNSPLASH_ACCESS_KEY: Unsplash API 访问密钥

获取 API 密钥步骤：
1. 访问 https://unsplash.com/oauth/applications
2. 创建一个新应用
3. 获取 Access Key
4. 设置环境变量: export UNSPLASH_ACCESS_KEY="your_access_key"
"""

import os
import requests
from typing import List, Optional, Dict
import warnings
from urllib.parse import quote

# ============= 配置常量 =============

UNSPLASH_API_BASE_URL = "https://api.unsplash.com"
UNSPLASH_SEARCH_ENDPOINT = f"{UNSPLASH_API_BASE_URL}/search/photos"

# 从环境变量读取 API 密钥
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')

# 请求超时时间（秒）
REQUEST_TIMEOUT = 10

# 单次请求最大结果数
MAX_RESULTS_PER_REQUEST = 30


# ============= 辅助函数 =============

def _is_valid_hex_color(color: Optional[str]) -> bool:
    """
    验证颜色是否为有效的 HEX 格式（不带 #）。
    
    Args:
        color (Optional[str]): 颜色字符串
        
    Returns:
        bool: 是否有效
    """
    if color is None or not isinstance(color, str):
        return True  # None 表示不指定颜色，是有效的
    
    # 去掉前导的 #
    color = color.lstrip('#')
    
    # 检查长度和字符
    if len(color) not in (3, 6):
        return False
    
    return all(c in '0123456789ABCDEFabcdef' for c in color)


def _normalize_hex_color(color: Optional[str]) -> Optional[str]:
    """
    规范化 HEX 颜色格式（去掉 #，转为小写）。
    
    Args:
        color (Optional[str]): 颜色字符串
        
    Returns:
        Optional[str]: 规范化后的颜色，如果为 None 则返回 None
    """
    if color is None:
        return None
    
    color = str(color).lstrip('#').lower()
    
    # 如果是 3 位颜色码，扩展为 6 位
    if len(color) == 3:
        color = ''.join(c * 2 for c in color)
    
    return color


# ============= 主要函数 =============

def fetch_web_images(
    query: str,
    color: Optional[str] = None,
    per_page: int = 10
) -> List[str]:
    """
    从 Unsplash API 获取符合条件的图片 URL。
    
    需要设置环境变量 UNSPLASH_ACCESS_KEY，获取方式：
    1. 访问 https://unsplash.com/oauth/applications
    2. 创建应用并获取 Access Key
    3. export UNSPLASH_ACCESS_KEY="your_key"
    
    Args:
        query (str): 搜索词，如 "sunset", "nature", "cat" 等
        color (Optional[str]): 颜色过滤，HEX 格式（可带或不带 #），
                               如 "#FF0000" 或 "FF0000"。
                               支持 Unsplash 的预定义颜色：
                               black, white, yellow, orange, red, purple, 
                               magenta, green, teal, blue 等。
                               如果不指定则不过滤。
        per_page (int): 每次请求返回的结果数，范围 1-30，默认 10
        
    Returns:
        List[str]: 图片 URL 列表。
                   若 API 密钥未设置、网络错误、超时等情况下返回空列表。
                   
    Raises:
        ValueError: 如果 query 为空或 per_page 超出范围
        
    Example:
        # 基础使用
        >>> urls = fetch_web_images("sunset", per_page=5)
        >>> print(urls[0])  # 返回第一张图片的 URL
        
        # 按颜色过滤
        >>> urls = fetch_web_images("flower", color="#FF0000", per_page=5)
        
        # 使用预定义颜色
        >>> urls = fetch_web_images("car", color="red", per_page=3)
    """
    
    # ===== 参数验证 =====
    
    if not query or not isinstance(query, str):
        raise ValueError("query 必须是非空字符串")
    
    if not 1 <= per_page <= 30:
        raise ValueError(f"per_page 必须在 1-30 之间，得到: {per_page}")
    
    if not _is_valid_hex_color(color):
        raise ValueError(f"无效的颜色格式: {color}。应为 HEX 格式或预定义颜色名。")
    
    # ===== API 密钥检查 =====
    
    if not UNSPLASH_ACCESS_KEY:
        warnings.warn(
            "❌ Unsplash API 密钥未设置。请按以下步骤配置：\n"
            "1. 访问 https://unsplash.com/oauth/applications\n"
            "2. 创建一个新应用\n"
            "3. 复制 Access Key\n"
            "4. 在终端运行: export UNSPLASH_ACCESS_KEY='your_access_key'\n"
            "5. 重新启动应用\n",
            UserWarning
        )
        return []
    
    # ===== 构建请求 =====
    
    # 请求头
    headers = {
        'Accept-Version': 'v1',
        'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}',
        'User-Agent': 'picolour-color-inspiration-tool/1.0'
    }
    
    # 查询参数
    params = {
        'query': query,
        'per_page': per_page,
        'order_by': 'relevant',
    }
    
    # 添加颜色过滤（如果提供）
    if color:
        normalized_color = _normalize_hex_color(color)
        params['color'] = normalized_color if normalized_color else color
    
    # ===== 发送请求 =====
    
    try:
        print(f"🔍 正在搜索 Unsplash: query='{query}', color={color}, per_page={per_page}")
        
        response = requests.get(
            UNSPLASH_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        
        # 检查 HTTP 状态码
        if response.status_code == 401:
            warnings.warn(
                "❌ Unsplash API 认证失败。请检查 UNSPLASH_ACCESS_KEY 是否正确设置。\n"
                "获取方式: https://unsplash.com/oauth/applications",
                UserWarning
            )
            return []
        
        elif response.status_code == 403:
            warnings.warn(
                "⚠️  API 速率限制已达到。请在一小时后重试。\n"
                "Unsplash 免费计划限制: 50 请求/小时",
                UserWarning
            )
            return []
        
        elif response.status_code == 404:
            warnings.warn(
                f"⚠️  搜索词 '{query}' 未找到相关图片。请尝试其他搜索词。",
                UserWarning
            )
            return []
        
        elif response.status_code != 200:
            warnings.warn(
                f"❌ API 请求失败，状态码: {response.status_code}\n"
                f"响应: {response.text[:200]}",
                UserWarning
            )
            return []
        
        # ===== 解析响应 =====
        
        data = response.json()
        
        if 'results' not in data:
            warnings.warn(
                "⚠️  API 返回格式异常，无法解析。",
                UserWarning
            )
            return []
        
        results = data['results']
        
        if not results:
            print(f"⚠️  搜索 '{query}' 无结果。")
            return []
        
        # 提取图片 URL
        image_urls = []
        for item in results:
            if 'urls' in item and 'regular' in item['urls']:
                image_urls.append(item['urls']['regular'])
        
        print(f"✓ 成功获取 {len(image_urls)} 张图片")
        return image_urls
    
    # ===== 错误处理 =====
    
    except requests.exceptions.Timeout:
        warnings.warn(
            f"❌ 网络请求超时（{REQUEST_TIMEOUT}秒）。\n"
            "可能原因：网络连接缓慢或 Unsplash 服务器响应慢。\n"
            "请检查网络连接并重试。",
            UserWarning
        )
        return []
    
    except requests.exceptions.ConnectionError:
        warnings.warn(
            "❌ 网络连接失败。\n"
            "可能原因：网络未连接或 Unsplash 服务器不可达。\n"
            "请检查网络连接。",
            UserWarning
        )
        return []
    
    except requests.exceptions.RequestException as e:
        warnings.warn(
            f"❌ HTTP 请求异常: {str(e)}",
            UserWarning
        )
        return []
    
    except ValueError as e:
        warnings.warn(
            f"❌ JSON 解析失败: {str(e)}",
            UserWarning
        )
        return []
    
    except Exception as e:
        warnings.warn(
            f"❌ 未预期的错误: {type(e).__name__}: {str(e)}",
            UserWarning
        )
        return []


# ============= 高级函数 =============

def fetch_web_images_by_palette(
    palette_colors: List[str],
    base_query: str = "nature",
    per_page: int = 5
) -> Dict[str, List[str]]:
    """
    根据调色板中的多个颜色分别搜索图片。
    
    Args:
        palette_colors (List[str]): HEX 颜色列表
        base_query (str): 基础搜索词，默认 "nature"
        per_page (int): 每个颜色搜索的图片数，默认 5
        
    Returns:
        Dict[str, List[str]]: 字典，键为颜色，值为对应的图片 URL 列表
        
    Example:
        >>> palette = ['#FF0000', '#00FF00', '#0000FF']
        >>> results = fetch_web_images_by_palette(palette, base_query='flower')
        >>> print(results['#FF0000'])  # 红色相关的图片 URL
    """
    results = {}
    
    for color in palette_colors:
        normalized_color = _normalize_hex_color(color)
        print(f"\n正在获取 {color} 相关的图片...")
        
        urls = fetch_web_images(
            query=base_query,
            color=color,
            per_page=per_page
        )
        
        results[color] = urls
    
    return results


def get_api_status() -> Dict:
    """
    检查 Unsplash API 连接状态。
    
    Returns:
        Dict: 包含以下字段：
            - api_key_set: API 密钥是否已设置
            - connection_ok: 是否能连接到 Unsplash 服务器
            - message: 状态信息
            
    Example:
        >>> status = get_api_status()
        >>> if status['connection_ok']:
        ...     print("API 连接正常")
    """
    status = {
        'api_key_set': bool(UNSPLASH_ACCESS_KEY),
        'connection_ok': False,
        'message': ''
    }
    
    if not UNSPLASH_ACCESS_KEY:
        status['message'] = 'API 密钥未设置'
        return status
    
    try:
        # 尝试一个简单的请求来检查连接
        headers = {
            'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}',
            'Accept-Version': 'v1'
        }
        
        response = requests.get(
            f"{UNSPLASH_API_BASE_URL}/me",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            status['connection_ok'] = True
            status['message'] = 'API 连接正常'
        elif response.status_code == 401:
            status['message'] = 'API 密钥无效'
        else:
            status['message'] = f'API 返回状态码 {response.status_code}'
        
    except Exception as e:
        status['message'] = f'连接失败: {str(e)}'
    
    return status


# ============= 使用示例 =============

if __name__ == '__main__':
    """
    模块使用示例和测试
    """
    
    print("在线搜索模块示例")
    print("=" * 60)
    
    # 1. 检查 API 状态
    print("\n1. 检查 API 连接状态:")
    print("-" * 60)
    status = get_api_status()
    print(f"API 密钥已设置: {status['api_key_set']}")
    print(f"连接状态: {status['message']}")
    
    if not status['api_key_set']:
        print("\n💡 请先设置 UNSPLASH_ACCESS_KEY:")
        print("   export UNSPLASH_ACCESS_KEY='your_access_key'")
        print("   获取链接: https://unsplash.com/oauth/applications")
    else:
        # 2. 基础搜索示例
        print("\n2. 基础图片搜索:")
        print("-" * 60)
        try:
            urls = fetch_web_images("sunset", per_page=3)
            if urls:
                print(f"✓ 获取了 {len(urls)} 张图片:")
                for i, url in enumerate(urls, 1):
                    print(f"  {i}. {url[:60]}...")
        except ValueError as e:
            print(f"❌ 错误: {e}")
        
        # 3. 按颜色搜索
        print("\n3. 按颜色搜索:")
        print("-" * 60)
        try:
            urls = fetch_web_images("flower", color="red", per_page=3)
            if urls:
                print(f"✓ 获取了 {len(urls)} 张红色花卉图片")
        except ValueError as e:
            print(f"❌ 错误: {e}")
        
        # 4. 调色板搜索
        print("\n4. 根据调色板搜索:")
        print("-" * 60)
        palette = ['#FF0000', '#00FF00']
        results = fetch_web_images_by_palette(
            palette,
            base_query='abstract',
            per_page=2
        )
        print(f"✓ 按调色板搜索完成，共 {sum(len(v) for v in results.values())} 张图片")

