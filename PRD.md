# DeepMemory 产品需求文档 (PRD)

| 项目名称 | DeepMemory |
| :--- | :--- |
| 版本号 | V1.0 |
| 状态 | 待开发 |
| 核心理念 | 上帝视角审视人际关系与记忆 |
| 平台 | Python Streamlit (Local Host) |

---

## 1. 项目愿景 (Product Vision)
**DeepMemory** 不仅仅是一个日记应用，它是一个**个人关系的动态拓扑图**。它利用图论（Graph Theory）将线性的记忆碎片转化为网状的结构，帮助用户跳出主观视角，以“上帝视角”重新审视自己与他人、地点、事件的关联。结合计算机视觉技术，它赋予记忆“感知能力”，主动协助用户构建社交网络图谱。

**核心隐喻：** 每一个遇到的人都是一个**节点 (Node)**，每一次共同经历都是连接彼此的**边 (Edge)**。

---

## 2. 用户体验设计 (UX Design)

### 2.1 设计风格
*   **关键词**：唯美 (Aesthetic)、怀旧 (Nostalgic)、极简 (Minimalist)、深邃 (Profound)。
*   **视觉语言**：
    *   背景采用低饱和度、纸质纹理或深空黑，强调“沉浸感”。
    *   图谱节点采用发光粒子效果，连线如神经元般连接。
    *   字体选择衬线体（Serif），营造文学与记录的庄重感。

### 2.2 交互原则
*   **轻量化**：单机运行，无复杂配置，数据掌握在用户手中（JSON Storage）。
*   **主动性**：AI 不仅是被动记录，更是主动提问者（Interactive Memory）。
*   **流动性**：图谱随操作实时动态重排，展现关系的流动。

---

## 3. 功能模块详解 (Functional Requirements)

### 3.1 核心模块：上帝视角 (God's View / The Graph)
首页即是图谱，这是产品的灵魂。

*   **功能描述**：
    *   基于力导向图 (Force-Directed Graph) 展示关系网络。
    *   **默认视图**：以用户 "Me" 为绝对中心，辐射状连接所有一级联系人。
    *   **节点 (Nodes)**：
        *   类型区分：人 (Person)、地点 (Location)。
        *   大小/颜色：根据权重（交互频率/共同记忆数量）动态变化。
    *   **边 (Edges)**：
        *   代表共同经历的事件。
        *   连线粗细代表关系的深浅。
*   **交互操作**：
    *   **缩放/拖拽**：自由探索图谱。
    *   **重中心化 (Re-centering)**：点击任意节点（如 "Alice"），图谱重新排列，以 "Alice" 为中心，展示 "Me" 与 "Alice" 的共同邻居（K=1 或 K=2 的子图）。
    *   **悬停 (Hover)**：鼠标悬停在边上，显示最近一次共同事件的摘要。

### 3.2 核心模块：时光日记 (Journal Entry)
数据的录入入口。

*   **功能描述**：
    *   **文本输入**：支持 Markdown 格式，记录当下的想法或事件。
    *   **媒体上传**：支持上传单张或多张照片。
    *   **元数据自动提取**：
        *   时间（从 Exif 读取或当前时间）。
        *   地点（可选手动输入或 Exif GPS）。
*   **逻辑流**：
    1. 用户输入文本 & 上传照片。
    2. 触发 **3.3 交互式记忆** 流程。
    3. 确认后生成一条 Event 数据，并在图谱中更新边和节点的权重。

### 3.3 核心模块：交互式记忆 (Interactive Memory)
这是本产品的“智能”核心，通过 AI 视觉分析完善图谱。

*   **AI 视觉分析 (Face Recognition)**：
    *   利用 `face_recognition` 库分析上传照片中的人脸。
    *   **已知面孔**：自动匹配已有节点 ID。
    *   **未知面孔**：检测到新的人脸特征向量。
*   **主动询问机制 (Active Query Protocol)**：
    *   当发现未知面孔时，界面弹出交互卡片：
        *   展示裁剪出的人脸特写（或在原图中标注）。
        *   **提问文案**：“这张照片里，穿[颜色/特征]的人是谁？”（简化版：高亮显示并问“这是谁？”）
    *   **用户决策**：
        *   *选项 A：关联已有节点*（"这是 Bob，换了发型"）。
        *   *选项 B：新建节点*（输入新名字 "Charlie" -> 系统创建新 Node 并存储人脸特征）。
        *   *选项 C：忽略*（路人甲）。

---

## 4. 数据结构设计 (Local Data Schema)

采用纯 JSON 文件存储，保存在 `./data/` 目录下。

### 4.1 `nodes.json` (人物与地点)
```json
[
  {
    "id": "uuid-001",
    "name": "Me",
    "type": "self",
    "face_encoding": [], // 用户的面部特征向量（可选）
    "created_at": "2023-01-01"
  },
  {
    "id": "uuid-002",
    "name": "Alice",
    "type": "person",
    "face_encoding": [0.12, -0.45, ...], // 128D 向量
    "relation_strength": 15
  }
]
```

### 4.2 `events.json` (记忆事件)
```json
[
  {
    "id": "evt-20251227-01",
    "date": "2025-12-27",
    "content": "和 Alice 在海边看日落。",
    "images": ["img_01.jpg"],
    "related_nodes": ["uuid-002", "uuid-005"] // 关联的人ID
  }
]
```

### 4.3 `edges.json` (关系连线 - 可动态计算，也可缓存)
*注：实际运行时可根据 `events.json` 动态构建 `edges`，无需强存储，但为了性能可缓存。*
```json
[
  {
    "source": "uuid-001", // Me
    "target": "uuid-002", // Alice
    "weight": 5, // 共同经历了5件事
    "last_interaction": "2025-12-27"
  }
]
```

---

## 5. 用户流程图 (User Flow)

1.  **启动应用**
    *   加载 `nodes.json` 和 `events.json`。
    *   渲染 **God's View** 首页。
2.  **添加记忆**
    *   点击侧边栏 "New Memory"。
    *   上传照片 -> **系统处理中 (Spinner)**。
3.  **AI 介入**
    *   系统检测到 2 张脸。
    *   Face A -> 匹配 "Alice" (置信度 > 0.6) -> 自动关联。
    *   Face B -> 未知 -> **弹窗询问**："检测到新朋友，他是谁？"
    *   用户输入："My Cat" (或 "Bob")。
4.  **生成图谱**
    *   系统保存 Event。
    *   系统更新 "Me"-"Alice" 的边权重。
    *   系统创建 "Me"-"Bob" 的新边。
    *   页面重定向回首页，图谱刷新，新节点出现。

---

## 6. 技术栈建议 (Tech Stack)

*   **Frontend/App Framework**: Streamlit (快速构建数据应用)。
*   **Visualization**:
    *   `streamlit-agraph`: 专门用于 Streamlit 的图论可视化组件（支持节点拖拽、配置）。
    *   或者 `pyvis`: 生成 HTML 交互图嵌入 Streamlit。
*   **Computer Vision**:
    *   `face_recognition` (基于 dlib): 简单易用的人脸识别 Python 库。
    *   `Pillow (PIL)`: 图像处理。
*   **Data Handling**: Python内建 `json`, `pandas`。
*   **Logic**: `networkx` (处理图的算法逻辑，如计算最短路径、邻居节点)。

## 7. 待办事项 (Implementation Roadmap)

1.  [ ] 初始化项目结构与 JSON 数据存储类。
2.  [ ] 实现 Streamlit 基础布局与 "时光日记" 录入功能。
3.  [ ] 集成 `face_recognition` 实现照片人脸检测。
4.  [ ] 开发 "主动询问" UI 逻辑 (Streamlit 表单交互)。
5.  [ ] 引入 `streamlit-agraph` 实现首页动态图谱。
6.  [ ] 优化 UI 样式 (Custom CSS)。
