import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st


# --- 初始化 Session State ---
DEFAULT_MINUTES = 25
# Obsidian 路径默认值
DEFAULT_OBSIDIAN_PATH = r"C:\Utopia\TheLibraryAtMountChar\MyDaily"

if "remaining_secs" not in st.session_state:
    st.session_state.remaining_secs = DEFAULT_MINUTES * 60
if "running" not in st.session_state:
    st.session_state.running = False
if "last_tick" not in st.session_state:
    st.session_state.last_tick = time.time()
if "task_name" not in st.session_state:
    st.session_state.task_name = ""
if "history" not in st.session_state:
    st.session_state.history = []
if "just_completed" not in st.session_state:
    st.session_state.just_completed = False
if "prev_remaining" not in st.session_state:
    st.session_state.prev_remaining = DEFAULT_MINUTES * 60
# 初始化 Obsidian 路径（只在第一次打开时使用默认值）
if "obsidian_path" not in st.session_state:
    st.session_state.obsidian_path = DEFAULT_OBSIDIAN_PATH
if "show_completion_dialog" not in st.session_state:
    st.session_state.show_completion_dialog = False
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "audio_file_name" not in st.session_state:
    st.session_state.audio_file_name = None
if "audio_file_bytes" not in st.session_state:
    st.session_state.audio_file_bytes = None
if "audio_file_type" not in st.session_state:
    st.session_state.audio_file_type = None


# --- 页面样式 ---
st.set_page_config(page_title="番茄钟 · Pomodoro", page_icon="⏳", layout="centered")

dark_style = """
<style>
body {
    background-color: #0d1117;
    color: #e6edf3;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.timer {
    font-size: 6rem;
    font-weight: 700;
    text-align: center;
    letter-spacing: 0.08em;
    color: #e6edf3;
    margin: 1.5rem 0 0.5rem 0;
}
.subtitle {
    text-align: center;
    color: #9ba5b1;
    margin-bottom: 1rem;
}
.task-input {
    margin-bottom: 1.5rem;
}
.stTextInput>div>div>input {
    background-color: #161b22;
    border: 2px solid #30363d;
    color: #e6edf3;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 1rem;
}
.stTextInput>div>div>input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.stButton>button {
    width: 100%;
    background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
    border: none;
    color: #f8fafc;
    font-weight: 600;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3), 
                0 2px 5px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
    font-size: 1rem;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4), 
                0 4px 8px rgba(0, 0, 0, 0.3);
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
}
.stButton>button:active {
    transform: translateY(0);
    box-shadow: 0 2px 10px rgba(37, 99, 235, 0.3);
}
button[kind="secondary"] {
    background: linear-gradient(135deg, #374151 0%, #1f2937 100%) !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
}
button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #4b5563 0%, #374151 100%) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4) !important;
}
button[kind="secondary"]:active {
    transform: translateY(0) !important;
}
.history-section {
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #30363d;
}
.history-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 1rem;
}
.history-item {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.history-task {
    font-weight: 500;
    color: #e6edf3;
}
.history-time {
    color: #9ba5b1;
    font-size: 0.9rem;
}
</style>
"""
st.markdown(dark_style, unsafe_allow_html=True)


# --- 侧边栏设置 ---
with st.sidebar:
    st.markdown("### ⚙️ 设置")
    st.markdown("---")
    
    obsidian_path = st.text_input(
        "Obsidian 每日笔记路径",
        value=st.session_state.obsidian_path,
        placeholder="例如: D:\\MyObsidianVault\\Daily",
        help="输入你的 Obsidian 每日笔记文件夹的完整路径",
        key="obsidian_path"
    )
    
    if obsidian_path:
        path = Path(obsidian_path.strip())
        if path.exists() and path.is_dir():
            st.success("✅ 路径有效")
        else:
            st.warning("⚠️ 路径不存在或不是文件夹")
    
    st.markdown("---")
    st.markdown("### 🎵 音乐播放")
    
    # 音乐文件上传
    uploaded_file = st.file_uploader(
        "选择音乐文件",
        type=['mp3', 'wav', 'ogg', 'm4a'],
        help="支持 MP3, WAV, OGG, M4A 格式",
        key="audio_uploader"
    )
    
    if uploaded_file is not None:
        # 保存文件信息到 session_state
        if "audio_file_name" not in st.session_state or st.session_state.audio_file_name != uploaded_file.name:
            st.session_state.audio_file_name = uploaded_file.name
            st.session_state.audio_file_bytes = uploaded_file.read()
            st.session_state.audio_file_type = uploaded_file.name.split('.')[-1]
        
        st.success(f"✅ 已加载: {uploaded_file.name}")
        
        # 显示音频播放器
        st.audio(st.session_state.audio_file_bytes, format=f"audio/{st.session_state.audio_file_type}")
        
        if st.button("清除音乐", key="clear_audio"):
            st.session_state.audio_file = None
            st.session_state.audio_file_name = None
            st.session_state.audio_file_bytes = None
            st.session_state.audio_file_type = None
            st.rerun()
    elif "audio_file_bytes" in st.session_state and st.session_state.audio_file_bytes is not None:
        # 如果之前有上传的文件，继续显示播放器
        st.info(f"📻 当前播放: {st.session_state.audio_file_name}")
        st.audio(st.session_state.audio_file_bytes, format=f"audio/{st.session_state.audio_file_type}")
        if st.button("清除音乐", key="clear_audio_existing"):
            st.session_state.audio_file = None
            st.session_state.audio_file_name = None
            st.session_state.audio_file_bytes = None
            st.session_state.audio_file_type = None
            st.rerun()


# --- 工具函数 ---
def format_mmss(seconds: float) -> str:
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


def generate_markdown_content(history: list) -> tuple[str, str]:
    """
    生成今日专注记录的 Markdown 内容
    
    Args:
        history: 历史记录列表
    
    Returns:
        (markdown内容, 文件名)
    """
    # 获取今日记录
    today = datetime.now().strftime("%Y-%m-%d")
    today_history = [h for h in history if h["date"] == today]
    
    if not today_history:
        return "", ""
    
    # 生成 Markdown 内容（使用新格式）
    markdown_lines = []
    markdown_lines.append("### 🍅 番茄钟记录")
    
    for record in today_history:
        task = record["task"]
        time_str = record.get("time", "")  # 获取时间（小时:分钟格式）
        markdown_lines.append(f"- [x] {task} (25分钟)")
        if time_str:
            markdown_lines.append(f"  - 执行时间: {time_str}")
    
    # 格式：\n\n### 🍅 番茄钟记录\n 加上列表
    markdown_content = "\n\n" + "\n".join(markdown_lines)
    
    # 生成文件名（使用日期格式，例如：2024-01-15.md）
    filename = f"{today}.md"
    
    return markdown_content, filename


def export_to_obsidian(obsidian_path: str, history: list) -> tuple[bool, str]:
    """
    归档今日专注记录到 Obsidian
    
    Args:
        obsidian_path: Obsidian 每日笔记文件夹路径
        history: 历史记录列表
    
    Returns:
        (成功标志, 消息)
    """
    if not obsidian_path or not obsidian_path.strip():
        return False, "请先设置 Obsidian 每日笔记路径"
    
    # 检查路径是否存在
    path = Path(obsidian_path.strip())
    if not path.exists():
        return False, f"❌ 路径不存在: {obsidian_path}"
    
    if not path.is_dir():
        return False, f"❌ 路径不是文件夹: {obsidian_path}"
    
    # 生成 Markdown 内容
    markdown_content, filename = generate_markdown_content(history)
    
    if not markdown_content:
        return False, "今日暂无专注记录"
    
    filepath = path / filename
    
    # 检查文件是否存在，如果存在则追加，否则创建
    try:
        if filepath.exists():
            # 读取现有内容
            existing_content = filepath.read_text(encoding="utf-8")
            
            # 追加到文件末尾（格式：\n\n### 🍅 番茄钟记录\n 加上列表）
            if existing_content.strip():
                # 如果文件不为空，追加内容（包含开头的 \n\n）
                new_content = existing_content.rstrip() + markdown_content + "\n"
            else:
                # 如果文件为空，去掉开头的换行符（文件开头不需要换行）
                new_content = markdown_content.lstrip() + "\n"
            filepath.write_text(new_content, encoding="utf-8")
        else:
            # 创建新文件（去掉开头的换行符，文件开头不需要换行）
            new_content = markdown_content.lstrip() + "\n"
            filepath.write_text(new_content, encoding="utf-8")
        
        return True, f"✅ 成功归档到: {filepath}"
    except Exception as e:
        return False, f"❌ 归档失败: {str(e)}"


def update_timer():
    if not st.session_state.running:
        return
    now = time.time()
    elapsed = now - st.session_state.last_tick
    st.session_state.remaining_secs = max(0.0, st.session_state.remaining_secs - elapsed)
    st.session_state.last_tick = now
    
    # 检测完成事件
    if st.session_state.remaining_secs <= 0 and st.session_state.prev_remaining > 0:
        st.session_state.running = False
        st.session_state.just_completed = True
        # 记录历史
        task = st.session_state.task_name if st.session_state.task_name else "未命名任务"
        current_time = datetime.now().strftime("%H:%M")
        st.session_state.history.insert(0, {
            "task": task,
            "time": current_time,
            "date": datetime.now().strftime("%Y-%m-%d")
        })
    
    st.session_state.prev_remaining = st.session_state.remaining_secs


# --- 计时更新 ---
update_timer()


# --- 布局 ---
st.markdown("<h2 style='text-align:center;'>专注 25 分钟</h2>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>保持专注，完成一小段高质量工作</p>", unsafe_allow_html=True)

# 任务输入框
task_name = st.text_input(
    "当前任务",
    value=st.session_state.task_name,
    placeholder="输入你的专注任务，例如：学习 Python",
    key="task_input",
    label_visibility="collapsed"
)
st.session_state.task_name = task_name

st.markdown(f"<div class='timer'>{format_mmss(st.session_state.remaining_secs)}</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    if st.button("▶️ 开始", use_container_width=True, type="primary"):
        if not st.session_state.running:
            st.session_state.running = True
            st.session_state.last_tick = time.time()
            st.session_state.just_completed = False
            # 如果剩余时间为0，重置计时器
            if st.session_state.remaining_secs <= 0:
                st.session_state.remaining_secs = DEFAULT_MINUTES * 60
                st.session_state.prev_remaining = DEFAULT_MINUTES * 60

with col2:
    if st.button("⏸️ 暂停", key="pause", use_container_width=True, type="secondary"):
        st.session_state.running = False

with col3:
    if st.button("🔄 重置", key="reset", use_container_width=True, type="secondary"):
        st.session_state.running = False
        st.session_state.remaining_secs = DEFAULT_MINUTES * 60
        st.session_state.prev_remaining = DEFAULT_MINUTES * 60
        st.session_state.last_tick = time.time()
        st.session_state.just_completed = False


# --- 完成反馈 ---
if st.session_state.just_completed and not st.session_state.show_completion_dialog:
    st.session_state.show_completion_dialog = True
    st.session_state.just_completed = False

# 显示完成弹窗（使用 Streamlit 容器实现弹窗效果）
if st.session_state.show_completion_dialog:
    st.balloons()
    
    # 使用容器创建弹窗样式
    with st.container():
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 3px solid #3b82f6;
            border-radius: 20px;
            padding: 2.5rem;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7);
            margin: 2rem 0;
        ">
            <h2 style="color: #3b82f6; margin-bottom: 1rem; font-size: 2.5rem;">🎉 专注完成！</h2>
            <p style="font-size: 1.3rem; margin-bottom: 2rem; color: #e6edf3;">恭喜你完成了一个番茄钟！</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 确认按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ 确认", use_container_width=True, type="primary", key="confirm_completion"):
                st.session_state.show_completion_dialog = False
                st.rerun()
    
    # 播放提示音（使用 Web Audio API 生成提示音）
    audio_html = """
    <script>
        (function() {
            try {
                var audioContext = new (window.AudioContext || window.webkitAudioContext)();
                var oscillator = audioContext.createOscillator();
                var gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                oscillator.frequency.value = 800;
                oscillator.type = 'sine';
                
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
                
                // 播放两次
                setTimeout(function() {
                    var oscillator2 = audioContext.createOscillator();
                    var gainNode2 = audioContext.createGain();
                    
                    oscillator2.connect(gainNode2);
                    gainNode2.connect(audioContext.destination);
                    
                    oscillator2.frequency.value = 1000;
                    oscillator2.type = 'sine';
                    
                    gainNode2.gain.setValueAtTime(0.3, audioContext.currentTime);
                    gainNode2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                    
                    oscillator2.start(audioContext.currentTime);
                    oscillator2.stop(audioContext.currentTime + 0.5);
                }, 600);
            } catch(e) {
                console.log('Audio play failed:', e);
            }
        })();
    </script>
    """
    st.markdown(audio_html, unsafe_allow_html=True)


# --- 今日专注记录 ---
today = datetime.now().strftime("%Y-%m-%d")
today_history = [h for h in st.session_state.history if h["date"] == today]

if today_history:
    st.markdown("<div class='history-section'>", unsafe_allow_html=True)
    st.markdown("<div class='history-title'>📊 今日专注记录</div>", unsafe_allow_html=True)
    
    for record in today_history:
        st.markdown(
            f"""
            <div class='history-item'>
                <span class='history-task'>{record['task']}</span>
                <span class='history-time'>{record['time']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # 归档和下载按钮
    st.markdown("<br>", unsafe_allow_html=True)
    col_archive, col_download = st.columns(2, gap="medium")
    
    with col_archive:
        if st.button("📥 归档到 Obsidian", use_container_width=True, type="primary"):
            success, message = export_to_obsidian(st.session_state.obsidian_path, st.session_state.history)
            if success:
                st.success(message, icon="✅")
            else:
                st.error(message, icon="❌")
    
    with col_download:
        # 生成 Markdown 内容用于下载
        markdown_content, filename = generate_markdown_content(st.session_state.history)
        # 确保文件名始终有效（使用今天的日期）
        if not filename:
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"{today}.md"
        
        if markdown_content:
            # 准备下载内容（去掉开头的换行符，文件开头不需要换行）
            download_content = markdown_content.lstrip() + "\n"
            st.download_button(
                label="💾 下载 Markdown",
                data=download_content.encode("utf-8"),
                file_name=filename,
                mime="text/markdown",
                use_container_width=True,
                type="secondary"
            )
        else:
            st.download_button(
                label="💾 下载 Markdown",
                data="",
                file_name=filename,
                mime="text/markdown",
                use_container_width=True,
                type="secondary",
                disabled=True
            )
    
    st.markdown("</div>", unsafe_allow_html=True)
elif st.session_state.obsidian_path:
    # 即使没有记录，如果设置了路径，也显示导出按钮（但会提示无记录）
    st.markdown("<div class='history-section'>", unsafe_allow_html=True)
    st.markdown("<div class='history-title'>📊 今日专注记录</div>", unsafe_allow_html=True)
    st.info("今日暂无专注记录", icon="ℹ️")
    st.markdown("<br>", unsafe_allow_html=True)
    col_archive2, col_download2 = st.columns(2, gap="medium")
    
    with col_archive2:
        if st.button("📥 归档到 Obsidian", key="archive_no_history", use_container_width=True, type="primary"):
            success, message = export_to_obsidian(st.session_state.obsidian_path, st.session_state.history)
            if success:
                st.success(message, icon="✅")
            else:
                st.error(message, icon="❌")
    
    with col_download2:
        # 生成 Markdown 内容用于下载
        markdown_content, filename = generate_markdown_content(st.session_state.history)
        if markdown_content:
            # 准备下载内容（去掉开头的换行符，文件开头不需要换行）
            download_content = markdown_content.lstrip() + "\n"
            st.download_button(
                label="💾 下载 Markdown",
                data=download_content.encode("utf-8"),
                file_name=filename,
                mime="text/markdown",
                use_container_width=True,
                type="secondary",
                key="download_no_history"
            )
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            st.download_button(
                label="💾 下载 Markdown",
                data="",
                file_name=f"{today}.md",
                mime="text/markdown",
                use_container_width=True,
                type="secondary",
                disabled=True,
                key="download_no_history_disabled"
            )
    st.markdown("</div>", unsafe_allow_html=True)

# --- 自动刷新实现平滑倒计时 ---
if st.session_state.running and st.session_state.remaining_secs > 0:
    time.sleep(1)
    st.rerun()

