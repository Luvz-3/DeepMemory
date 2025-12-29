# DeepMemory - 基于图谱的个人记忆星系

DeepMemory 是一个基于 Python Streamlit 和图论构建的个人记忆管理系统。它采用了独特的 "Midnight Liminal Space"（午夜阈限空间）视觉风格，将你的照片、日记和人际关系转化为一个可交互、会呼吸的动态星系图谱。

## ✨ 核心功能

* **🌌 关系星图 (Relationship Graph)**
    * 摒弃传统列表，用“星系”展示人际网络。
    * 节点如行星般发光，连线如星轨般交织。
    * 支持动态交互：拖拽、缩放、点击查看详情。

* **📥 时光胶囊 (Time Capsule)**
    * 记忆录入入口。上传照片或撰写日记。
    * **AI 辅助识别**：自动分析照片中的人物，智能构建关系网。

* **🖼️ 记忆画廊 (Memory Gallery)**
    * 你的私人博物馆。
    * 支持 **列表/网格** 双视图切换，按时间轴回顾所有珍贵时刻。
    * 支持对过往事件的编辑与修订。

* **🎨 沉浸式体验 (Vibe)**
    * **午夜阈限空间**风格：深蓝色的夜空背景，缓慢飘落的记忆星尘。
    * **磨砂玻璃**质感 UI，营造静谧、专注的回忆氛围。

## 🛠️ 技术栈

* **Python 3.8+**
* **Streamlit**: 核心 Web 框架
* **NetworkX**: 图论与关系计算
* **Streamlit-Agraph**: 图谱可视化组件 (基于 Vis.js)
* **Pillow**: 图像处理

## 🚀 快速开始

1.  **克隆项目**
    ```bash
    git clone https://github.com/your-username/deep-memory.git
    cd deep-memory
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **运行应用**
    ```bash
    streamlit run app.py
    ```

## ⚙️ 配置指南 (Configuration)

本项目依赖阿里云 DashScope 模型。运行前请配置 API Key：

1.  在项目根目录新建文件夹 `.streamlit`。
2.  在里面新建文件 `secrets.toml`。
3.  写入你的密钥：
    ```toml
    DASHSCOPE_API_KEY = "sk-你的阿里云密钥"
    ```
    *(注意：请勿将此文件上传到 GitHub)*

## 📝 许可证

[MIT License](LICENSE)