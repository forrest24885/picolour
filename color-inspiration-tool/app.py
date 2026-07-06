"""
色彩灵感工具 - Streamlit 应用
Color Inspiration Tool - Streamlit Application

功能：
1. Tab1 - 颜色灵感：颜色选择、互补色、三角色、渐变色预览、相似物象展示（本地+联网）
2. Tab2 - 形状与配色：绘图画布、配色方案推荐、参考图片展示

依赖：
- streamlit
- pillow
- pandas
- streamlit-drawable-canvas
- 本地模块：image_search, online_search

本地优先策略：
- 若本地 CSV 和图片完整，优先使用本地搜索
- 若本地数据缺失，自动切换到联网搜索（需要 UNSPLASH_ACCESS_KEY）
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import os
from PIL import Image
import numpy as np
import colorsys
import requests
import warnings
import json

# 尝试导入画布库，如果未安装则提示
try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

# 尝试导入本地搜索模块
try:
    import image_search as img_search
    IMAGE_SEARCH_AVAILABLE = True
except ImportError:
    IMAGE_SEARCH_AVAILABLE = False
    warnings.warn("image_search 模块未找到，本地搜索功能不可用")

# 尝试导入联网搜索模块
try:
    import online_search as online_srch
    ONLINE_SEARCH_AVAILABLE = True
except ImportError:
    ONLINE_SEARCH_AVAILABLE = False
    warnings.warn("online_search 模块未找到，联网搜索功能不可用")

# ============= 页面配置 =============
st.set_page_config(
    page_title="色彩灵感工具",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 美化
st.markdown("""
    <style>
    .color-block {
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


# ============= 数据检查和初始化 =============

def check_local_data_available() -> bool:
    """
    检查本地数据是否完整：CSV 文件存在、非空、且有对应的图片。
    
    Returns:
        bool: 本地数据是否可用
    """
    csv_path = Path('data/color_data.csv')
    images_dir = Path('data/images')
    
    # 检查 CSV 文件
    if not csv_path.exists():
        return False
    
    try:
        df = pd.read_csv(csv_path)
        if len(df) == 0:
            return False
        
        # 检查是否有对应的图片文件
        images_count = 0
        for _, row in df.iterrows():
            image_path = images_dir / row['image_path']
            if image_path.exists():
                images_count += 1
        
        return images_count > 0
    except Exception:
        return False


def get_color_search_keywords(hex_color: str) -> str:
    """
    根据 HEX 颜色自动生成搜索关键词。
    
    Args:
        hex_color (str): HEX 颜色码
        
    Returns:
        str: 搜索关键词
    """
    # 简化的颜色到关键词映射
    rgb = hex_to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    
    # 根据色调判断颜色
    hue_angle = h * 360
    
    if hue_angle < 30 or hue_angle >= 330:
        color_name = "red"
        object_type = "fruit"
    elif hue_angle < 60:
        color_name = "orange"
        object_type = "sunset"
    elif hue_angle < 90:
        color_name = "yellow"
        object_type = "flower"
    elif hue_angle < 150:
        color_name = "green"
        object_type = "nature"
    elif hue_angle < 210:
        color_name = "blue"
        object_type = "sky"
    elif hue_angle < 270:
        color_name = "purple"
        object_type = "flower"
    elif hue_angle < 330:
        color_name = "pink"
        object_type = "flower"
    else:
        color_name = "gray"
        object_type = "object"
    
    return f"{color_name} {object_type}"


@st.cache_resource
def init_local_search():
    """初始化本地图片搜索。"""
    try:
        if IMAGE_SEARCH_AVAILABLE:
            img_search.load_image_data('data/color_data.csv', 'data/images')
            return True
    except Exception as e:
        st.warning(f"⚠️ 本地数据初始化失败: {e}")
    return False


# 检查数据可用性
LOCAL_DATA_AVAILABLE = check_local_data_available()

# 缓存初始化状态
if LOCAL_DATA_AVAILABLE:
    init_local_search()

# ============= Session State 初始化 =============

if 'selected_color' not in st.session_state:
    st.session_state.selected_color = '#FF5733'

if 'selected_scheme' not in st.session_state:
    st.session_state.selected_scheme = None

if 'canvas_data' not in st.session_state:
    st.session_state.canvas_data = None

if 'last_search_color' not in st.session_state:
    st.session_state.last_search_color = None


# ============= 颜色计算函数 =============

def hex_to_rgb(hex_color):
    """
    将 HEX 颜色转换为 RGB 元组
    
    Args:
        hex_color (str): HEX 格式颜色，如 '#FF5733'
    
    Returns:
        tuple: RGB 元组，如 (255, 87, 51)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    """
    将 RGB 颜色转换为 HEX 格式
    
    Args:
        rgb (tuple): RGB 元组，如 (255, 87, 51)
    
    Returns:
        str: HEX 格式颜色，如 '#FF5733'
    """
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def get_complementary_color(hex_color):
    """
    获取互补色（对比色）
    
    原理：在 HSV 色彩空间中，互补色为色调相差 180 度
    
    Args:
        hex_color (str): HEX 格式颜色
    
    Returns:
        str: 互补色的 HEX 格式
    """
    rgb = hex_to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    h = (h + 0.5) % 1.0  # 色调旋转 180 度
    comp_rgb = colorsys.hsv_to_rgb(h, s, v)
    return rgb_to_hex((comp_rgb[0]*255, comp_rgb[1]*255, comp_rgb[2]*255))


def get_triadic_colors(hex_color):
    """
    获取三角色（三色和谐配色）
    
    原理：在色相环上均匀分布三个颜色，每个间隔 120 度
    
    Args:
        hex_color (str): HEX 格式颜色
    
    Returns:
        list: 三个 HEX 颜色的列表
    """
    rgb = hex_to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    
    h1 = h
    h2 = (h + 1/3) % 1.0
    h3 = (h + 2/3) % 1.0
    
    rgb1 = colorsys.hsv_to_rgb(h1, s, v)
    rgb2 = colorsys.hsv_to_rgb(h2, s, v)
    rgb3 = colorsys.hsv_to_rgb(h3, s, v)
    
    return [
        rgb_to_hex((rgb1[0]*255, rgb1[1]*255, rgb1[2]*255)),
        rgb_to_hex((rgb2[0]*255, rgb2[1]*255, rgb2[2]*255)),
        rgb_to_hex((rgb3[0]*255, rgb3[1]*255, rgb3[2]*255))
    ]


def get_gradient_colors(hex_color, steps=5):
    """
    生成从目标颜色到白色的渐变色
    
    Args:
        hex_color (str): HEX 格式颜色
        steps (int): 渐变步数，默认为 5
    
    Returns:
        list: HEX 颜色列表，从目标颜色渐变到白色
    """
    rgb = hex_to_rgb(hex_color)
    gradient = []
    for i in range(steps):
        ratio = i / (steps - 1)
        r = int(rgb[0] + (255 - rgb[0]) * ratio)
        g = int(rgb[1] + (255 - rgb[1]) * ratio)
        b = int(rgb[2] + (255 - rgb[2]) * ratio)
        gradient.append(rgb_to_hex((r, g, b)))
    return gradient


# ============= 数据加载函数 =============

def load_images_from_folder(folder_path):
    """
    从指定文件夹加载所有图片文件
    
    支持格式：.jpg, .jpeg, .png, .gif, .webp
    
    Args:
        folder_path (str): 文件夹路径
    
    Returns:
        list: 图片文件路径列表
    """
    images = []
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                images.append(os.path.join(folder_path, filename))
    return sorted(images)


def load_color_data():
    """
    从 CSV 文件加载颜色数据
    
    预期 CSV 格式：color_name, hex_code, rgb, description
    
    Returns:
        pd.DataFrame: 颜色数据框，如果文件不存在则返回空数据框
    """
    csv_path = Path('data/color_data.csv')
    if csv_path.exists():
        try:
            return pd.read_csv(csv_path)
        except Exception as e:
            st.warning(f"加载 CSV 文件出错: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


# ============= Session State 初始化 =============

if 'selected_color' not in st.session_state:
    st.session_state.selected_color = '#FF5733'

if 'selected_scheme' not in st.session_state:
    st.session_state.selected_scheme = None

if 'color_hue' not in st.session_state:
    st.session_state.color_hue = 0.0

if 'color_saturation' not in st.session_state:
    st.session_state.color_saturation = 1.0

if 'color_value' not in st.session_state:
    st.session_state.color_value = 1.0


# ============= 色环选择器函数 =============

def create_color_wheel_picker(label: str, key_prefix: str) -> str:
    """
    创建交互式环形色环选择器（HSV模式）
    
    Args:
        label: 选择器标签
        key_prefix: session state 的键前缀
        
    Returns:
        str: 选定的HEX颜色代码
    """
    st.subheader(label)
    
    # 创建三个列布局用于HSV控制
    col_h, col_s, col_v = st.columns(3)
    
    # 色调（Hue）- 0-360度，对应色环位置
    with col_h:
        hue = st.slider(
            "🌈 色调",
            min_value=0,
            max_value=360,
            value=int(st.session_state.color_hue * 360),
            step=1,
            key=f"{key_prefix}_hue"
        )
        st.session_state.color_hue = hue / 360.0
    
    # 饱和度（Saturation）
    with col_s:
        saturation = st.slider(
            "💧 饱和度",
            min_value=0,
            max_value=100,
            value=int(st.session_state.color_saturation * 100),
            step=1,
            key=f"{key_prefix}_sat"
        )
        st.session_state.color_saturation = saturation / 100.0
    
    # 明度（Value）
    with col_v:
        value = st.slider(
            "☀️ 明度",
            min_value=0,
            max_value=100,
            value=int(st.session_state.color_value * 100),
            step=1,
            key=f"{key_prefix}_val"
        )
        st.session_state.color_value = value / 100.0
    
    # 从HSV转换到RGB再到HEX
    rgb = colorsys.hsv_to_rgb(
        st.session_state.color_hue,
        st.session_state.color_saturation,
        st.session_state.color_value
    )
    hex_color = rgb_to_hex((rgb[0] * 255, rgb[1] * 255, rgb[2] * 255))
    
    # 绘制色环可视化
    st.markdown("#### 🎨 色环可视化")
    
    # 创建一个包含多个颜色块的行来表示色环
    color_wheel_cols = st.columns(12)
    for i in range(12):
        hue_angle = i / 12.0
        rgb_temp = colorsys.hsv_to_rgb(hue_angle, st.session_state.color_saturation, st.session_state.color_value)
        color_hex = rgb_to_hex((rgb_temp[0] * 255, rgb_temp[1] * 255, rgb_temp[2] * 255))
        
        with color_wheel_cols[i]:
            # 高亮当前选择的色调
            if abs(hue_angle - st.session_state.color_hue) < 0.05:
                st.markdown(
                    f'<div style="background-color: {color_hex}; height: 60px; border: 4px solid gold; border-radius: 8px;"></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div style="background-color: {color_hex}; height: 60px; border: 2px solid #ddd; border-radius: 8px; cursor: pointer;"></div>',
                    unsafe_allow_html=True
                )
    
    # 显示当前颜色的详细信息
    st.markdown("#### 📊 当前颜色")
    col_preview1, col_preview2 = st.columns([1, 1])
    
    with col_preview1:
        st.markdown(
            f'<div style="background-color: {hex_color}; height: 100px; border-radius: 10px; border: 2px solid #ddd;"></div>',
            unsafe_allow_html=True
        )
    
    with col_preview2:
        st.markdown(f"**HEX**: `{hex_color}`")
        st.markdown(f"**RGB**: `({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)})`")
        st.markdown(f"**HSV**: `({hue}°, {saturation}%, {value}%)`")
    
    return hex_color


# ============= 主应用页面 =============

# 页面标题和说明
st.title("🎨 色彩灵感工具")

# 显示运行模式
if LOCAL_DATA_AVAILABLE:
    st.markdown("✅ **本地模式** | 基于本地数据库的颜色探索和配色推荐 | 完全离线运行")
else:
    st.markdown("🌐 **混合模式** | 本地 + 联网搜索 | 若无本地数据，自动从 Unsplash 获取图片")

st.markdown("---")

# 创建两个 Tab
tab1, tab2 = st.tabs(["🎨 颜色灵感", "✏️ 形状与配色"])

# ============= TAB 1: 颜色灵感 =============
with tab1:
    st.header("颜色灵感探索")
    st.markdown("选择一个颜色，系统将为您展示其互补色、三角色、渐变色，以及现实中相似物象的参考图片。")
    
    col1, col2 = st.columns([1, 2])
    
    # 左列：颜色选择
    with col1:
        # 使用新的环形色环选择器替代color_picker
        color_input = create_color_wheel_picker("🎯 颜色选择器", "main_color")
        st.session_state.selected_color = color_input
    
    # 右列：颜色方案展示
    with col2:
        st.subheader("🌈 配色方案")
        
        # 每次重新计算配色（确保跟随颜色改变）
        comp_color = get_complementary_color(color_input)
        triadic = get_triadic_colors(color_input)
        gradient = get_gradient_colors(color_input, steps=5)
        
        # 实时显示当前颜色的信息
        st.info(f"✨ 当前主色: {color_input}")
        
        # 1. 互补色方案
        st.markdown("#### 1️⃣ 互补色配色方案")
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            st.color_picker(
                label="主色",
                value=color_input,
                disabled=True,
                key="main_comp_display"
            )
            st.caption(f"主色: {color_input}")
        with col_comp2:
            st.color_picker(
                label="互补色",
                value=comp_color,
                disabled=True,
                key="comp_color_display"
            )
            st.caption(f"互补色: {comp_color}")
        
        # 2. 三角色方案
        st.markdown("#### 2️⃣ 三角色配色方案（三色和谐）")
        col_tri1, col_tri2, col_tri3 = st.columns(3)
        colors_info = [
            (col_tri1, triadic[0], "色1"),
            (col_tri2, triadic[1], "色2"),
            (col_tri3, triadic[2], "色3")
        ]
        for col, color, label in colors_info:
            with col:
                st.color_picker(
                    label=label,
                    value=color,
                    disabled=True,
                    key=f"tri_color_{label}"
                )
                st.caption(f"{label}: {color}")
        
        # 3. 渐变色方案
        st.markdown("#### 3️⃣ 渐变色预览（到白色）")
        gradient_cols = st.columns(len(gradient))
        for i, (col, grad_color) in enumerate(zip(gradient_cols, gradient)):
            with col:
                st.color_picker(
                    label=f"步骤{i+1}",
                    value=grad_color,
                    disabled=True,
                    key=f"grad_color_{i}"
                )
                st.caption(f"步骤{i+1}")
    
    # 图片展示区域
    st.markdown("---")
    st.subheader("📸 现实/动画中的类似物象")
    
    # 判断使用本地还是联网搜索
    if LOCAL_DATA_AVAILABLE and IMAGE_SEARCH_AVAILABLE:
        # ===== 本地搜索模式 =====
        st.info("✅ 使用本地数据库搜索（无需网络）")
        
        try:
            results = img_search.search_by_color(color_input, top_n=12)
            
            if results:
                st.markdown(f"**共找到 {len(results)} 张相似颜色的图片**")
                
                cols = st.columns(4)
                for idx, result in enumerate(results):
                    with cols[idx % 4]:
                        try:
                            image_path = result['image_path']
                            if Path(image_path).exists():
                                img = Image.open(image_path)
                                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                                st.image(
                                    img,
                                    caption=f"{result['object_name']}\n({result['style']})\nΔE: {result['delta_e']:.2f}",
                                    use_column_width=True
                                )
                        except Exception as e:
                            st.warning(f"❌ 无法加载: {result['object_name']}")
            else:
                st.info("📁 未找到相似的本地图片")
        
        except Exception as e:
            st.error(f"❌ 本地搜索出错: {e}")
    
    else:
        # ===== 联网搜索模式 =====
        # 实时读取环境变量（支持动态配置）
        current_api_key = os.environ.get('UNSPLASH_ACCESS_KEY')
        
        if ONLINE_SEARCH_AVAILABLE and current_api_key:
            st.info("🌐 使用在线数据库搜索（Unsplash）")
            
            # 生成搜索关键词
            search_keyword = get_color_search_keywords(color_input)
            
            st.markdown(f"**搜索关键词**: `{search_keyword}` | **颜色**: `{color_input}`")
            st.write(f"🔑 **API 密钥状态**: ✅ 已配置")
        
            # 创建搜索按钮
            col_search1, col_search2 = st.columns([3, 1])
            with col_search2:
                search_button = st.button("🔍 搜索图片")
            
            if search_button or 'last_search_color' not in st.session_state:
                st.session_state.last_search_color = color_input
                
                with st.spinner("🔄 正在从 Unsplash 搜索图片..."):
                    try:
                        # 从网络获取图片
                        urls = online_srch.fetch_web_images(
                            query=search_keyword,
                            color=color_input,
                            per_page=12
                        )
                        
                        if urls:
                            st.markdown(f"✅ **共获取 {len(urls)} 张网络图片**")
                            
                            cols = st.columns(4)
                            for idx, url in enumerate(urls):
                                with cols[idx % 4]:
                                    try:
                                        st.image(url, use_column_width=True, caption=f"图片 {idx+1}")
                                    except Exception as e:
                                        st.warning(f"❌ 无法显示图片 {idx+1}")
                        else:
                            st.warning("⚠️ 未找到相关图片，请检查网络连接或尝试其他搜索词")
                    
                    except Exception as e:
                        st.error(f"❌ 联网搜索出错: {str(e)}")
                        st.write(f"**错误详情**: {e}")
            elif st.session_state.last_search_color == color_input:
                # 使用缓存的搜索结果（如果颜色没变）
                st.info("💡 提示：改变颜色后点击「搜索图片」按钮获取新结果")
        
        elif ONLINE_SEARCH_AVAILABLE and not current_api_key:
            # ===== 提示设置 API 密钥 =====
            st.warning("""
            ⚠️ **请设置 UNSPLASH_ACCESS_KEY 以启用联网搜索**
            
            本地数据缺失或为空，但 UNSPLASH_ACCESS_KEY 未配置。
            
            **快速配置**（在此目录运行）：
            ```bash
            export UNSPLASH_ACCESS_KEY="your_access_key"
            streamlit run app.py
            ```
            
            **获取 API 密钥步骤**：
            1. 访问 https://unsplash.com/oauth/applications
            2. 创建一个新应用
            3. 复制 Access Key
            4. 粘贴到上述命令中
            """)
        
        else:
            # ===== 既无本地数据也无联网能力 =====
            st.error("""
            ❌ **图片搜索功能不可用**
            
            原因：
            - 本地数据缺失（data/color_data.csv 不存在或为空）
            - Unsplash 服务不可用或 API 密钥未配置
            
            **解决方案**：
            1. 添加本地图片数据：
               - 将图片放入 `data/images/` 文件夹
               - 创建 `data/color_data.csv` 文件，格式: hex, object_name, style, image_path
            2. 或者配置 UNSPLASH_ACCESS_KEY 进行联网搜索（推荐）
            """)


# ============= TAB 2: 形状与配色 =============
with tab2:
    st.header("形状与配色方案")
    st.markdown("在画布上绘制形状，系统将自动推荐配色方案，并显示类似风格的参考图片。")
    
    # 检查绘图库是否可用
    if not CANVAS_AVAILABLE:
        st.error("""
        ❌ 缺少必要库: `streamlit-drawable-canvas`
        
        请运行以下命令安装：
        ```bash
        pip install streamlit-drawable-canvas
        ```
        """)
    
    col_canvas, col_palette = st.columns([1.5, 1], gap="large")
    
    # 左列：绘图画布
    with col_canvas:
        st.subheader("✏️ 绘图画布")
        
        with st.container(border=True):
            if CANVAS_AVAILABLE:
                # 创建可绘制的画布
                canvas_result = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=3,
                    stroke_color="rgba(0, 0, 0, 1)",
                    background_color="rgba(255, 255, 255, 1)",
                    height=450,
                    width=600,
                    drawing_mode="freedraw",
                    key="canvas",
                )
                
                st.caption("💡 用鼠标在画布上自由绘制形状")
                
                # 绘图模式说明
                st.markdown("""
                **当前模式**：自由绘制
                - 用鼠标在画布上绘制任意形状
                - 绘制完成后，右侧将自动显示推荐配色方案
                """)
                
                # 检查画布是否有绘制内容
                if canvas_result.json_data is not None:
                    try:
                        # 尝试从绘制数据中提取点信息
                        json_data = canvas_result.json_data
                        
                        # 检查是否有对象被绘制
                        if 'objects' in json_data and len(json_data['objects']) > 0:
                            st.session_state.canvas_data = json_data
                            st.success("✅ 检测到绘制内容！")
                        else:
                            st.session_state.canvas_data = None
                    except Exception as e:
                        st.warning(f"⚠️ 无法解析绘制数据: {e}")
            else:
                st.warning("画布功能不可用，请安装 streamlit-drawable-canvas")
                st.code("pip install streamlit-drawable-canvas")
    
    # 右列：配色方案推荐
    with col_palette:
        st.subheader("🎨 配色推荐")
        
        with st.container(border=True):
            # 检查是否有绘制内容
            if st.session_state.canvas_data is not None:
                st.success("✨ 基于你的绘制智能推荐配色方案")
                
                # 提取绘制的对象信息（简化处理）
                try:
                    objects = st.session_state.canvas_data.get('objects', [])
                    
                    if objects:
                        # 计算绘制的点数来判断形状复杂度
                        point_count = sum(len(obj.get('points', [])) for obj in objects if 'points' in obj)
                        
                        # 简单的形状分类启发式
                        if point_count < 50:
                            estimated_shape = "三角形"
                        elif point_count < 150:
                            estimated_shape = "方形"
                        elif point_count < 300:
                            estimated_shape = "有机形"
                        else:
                            estimated_shape = "圆形"
                        
                        st.info(f"📐 形状: **{estimated_shape}**")
                        
                        # 显示动态推荐配色
                        mood = st.selectbox(
                            "风格",
                            ["auto", "calm", "vibrant", "dark"],
                            format_func=lambda x: {"auto": "自动", "calm": "平静", "vibrant": "活力", "dark": "深色"}[x],
                            key="mood_selector"
                        )
                        
                        # 动态导入 shape_color 模块
                        try:
                            import shape_color as sc
                            palette = sc.recommend_palettes(estimated_shape, mood=mood)
                        except ImportError:
                            palette = ["#FF6B6B", "#FFA726", "#FFD93D", "#4ECDC4"]  # 默认配色
                        
                        # 显示推荐配色
                        st.markdown("#### 💎 推荐配色:")
                        cols = st.columns(len(palette))
                        for i, (col, color) in enumerate(zip(cols, palette)):
                            with col:
                                st.color_picker(
                                    label=f"色{i+1}",
                                    value=color,
                                    disabled=True,
                                    key=f"rec_color_{i}"
                                )
                        
                        st.caption(f"{' '.join(palette)}")
                        
                except Exception as e:
                    st.warning(f"⚠️ 分析失败: {e}")
                    st.info("💡 继续绘制...")
            
            else:
                # 无绘制内容时显示预定义方案
                st.markdown("在左边画布上绘制以获取推荐")
                st.markdown("---")
                
                # 预定义的配色方案库
                color_schemes = {
                    "方案 1 - 暖色调": {
                        "colors": ["#FF6B6B", "#FFA726", "#FFD93D"],
                        "description": "温暖、热烈的暖色系配色"
                    },
                    "方案 2 - 冷色调": {
                        "colors": ["#4ECDC4", "#44A5C2", "#2C3E50"],
                        "description": "清爽、冷静的蓝绿色系配色"
                    },
                    "方案 3 - 森林风": {
                        "colors": ["#2D6A4F", "#52B788", "#95D5B2"],
                        "description": "自然、宁静的绿色系配色"
                    },
                    "方案 4 - 日落风": {
                        "colors": ["#FF6B35", "#F7931E", "#FDB833"],
                        "description": "炽热、绚丽的橙红色系配色"
                    },
                    "方案 5 - 海洋风": {
                        "colors": ["#006BA6", "#0496FF", "#72DDF7"],
                        "description": "深邃、流畅的蓝色系配色"
                    },
                }
                
                st.markdown("### 📚 预定义配色方案:")
                # 显示所有配色方案
                for scheme_name, scheme_data in color_schemes.items():
                    colors = scheme_data["colors"]
                    description = scheme_data["description"]
                    
                    # 方案行布局
                    col_btn, col_colors = st.columns([1, 3])
                    
                    # 选择按钮
                    with col_btn:
                        if st.button(f"选择", key=f"btn_{scheme_name}", use_container_width=True):
                            st.session_state.selected_scheme = scheme_name
                            st.rerun()
                    
                    # 颜色块显示
                    with col_colors:
                        cols = st.columns(len(colors))
                        for col, color in zip(cols, colors):
                            with col:
                                st.color_picker(
                                    label=" ",
                                    value=color,
                                    disabled=True,
                                    key=f"scheme_{scheme_name}_{color}"
                                )
                    
                    # 方案描述
                    st.caption(f"📝 {description}")
                    st.divider()
                
                # 显示选中方案的参考图片
                if st.session_state.selected_scheme:
                    st.markdown("---")
                    st.markdown(f"""
                    #### 🖼️ 类似风格的参考图片
                **已选择**: {st.session_state.selected_scheme}
                """)
                
                    images_folder = Path('data/images')
                    image_files = load_images_from_folder(str(images_folder))
                    
                    if image_files:
                        # 显示参考图片
                        cols = st.columns(3)
                        for idx, image_path in enumerate(image_files[:6]):
                            with cols[idx % 3]:
                                try:
                                    img = Image.open(image_path)
                                    img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                                    st.image(img, caption=os.path.basename(image_path), use_column_width=True)
                                except Exception as e:
                                    st.warning(f"❌ 无法加载图片")
                    else:
                        st.info("📁 请在 'data/images/' 文件夹中添加参考图片")


# ============= 页脚 =============
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns([1, 1, 1])

with footer_col1:
    st.markdown("""
    ### 📁 文件结构
    ```
    data/
    ├── images/        (参考图片)
    └── color_data.csv (颜色数据)
    ```
    """)

with footer_col2:
    st.markdown("""
    ### 🛠️ 技术栈
    - **框架**: Streamlit
    - **颜色处理**: colorsys
    - **图片处理**: PIL (Pillow)
    - **数据**: pandas
    """)

with footer_col3:
    st.markdown("""
    ### 💡 使用提示
    1. 将参考图片放入 `data/images/`
    2. 在 Tab1 探索颜色方案
    3. 在 Tab2 绘制形状并获取推荐配色
    4. 完全离线运行，无需网络
    """)

st.markdown("✨ **色彩灵感工具** - 让设计变得更有灵感")
