# MySQL AI 查询工具 (MySQL AI Query Tool)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Web 的智能 MySQL 客户端工具，允许用户通过自然语言或直接编写 SQL 与数据库进行交互。它集成了 AI 模型将自然语言转换为 SQL，并提供了数据库结构浏览和表关系可视化功能。

## ✨ 主要功能

*   **数据库连接管理:**
    *   配置和连接到 MySQL 数据库 (主机, 端口, 用户名, 密码)。
    *   动态加载和选择数据库。
    *   测试数据库连接。
    *   保存和加载连接配置到本地存储。
*   **智能查询 (Natural Language Querying):**
    *   输入自然语言问题 (例如，"查找最近注册的10个用户")。
    *   AI 模型自动将问题转换为 SQL 查询语句。
    *   执行生成的 SQL 并展示结果。
    *   显示 AI 对查询的解释。
*   **直接 SQL 执行:**
    *   提供带有语法高亮和自动完成功能的 SQL 编辑器 (CodeMirror)。
    *   直接编写和执行 SQL 语句 (SELECT, INSERT, UPDATE, DELETE, CREATE 等)。
    *   清空 SQL 编辑器内容。
*   **结果展示:**
    *   使用 Tabulator.js 在交互式表格中显示查询结果。
    *   支持排序、过滤、分页。
    *   支持将结果导出为 CSV 或 JSON 文件。
*   **SQL 显示:**
    *   清晰展示由 AI 生成或用户直接输入的 SQL 语句。
*   **数据库探索:**
    *   **数据库结构:** 浏览选定数据库中的所有表及其列信息 (名称, 类型, 是否为空, 主键等)。
    *   **表关系图谱:** 使用 Vis.js 可视化展示表之间的外键关系。
*   **查询历史:**
    *   自动保存最近的查询记录 (自然语言问题, SQL, 部分结果, AI 解释)。
    *   一键加载历史查询及其结果。
    *   清空查询历史。
*   **用户体验:**
    *   支持浅色和深色主题模式切换。
    *   响应式设计，适应不同屏幕尺寸。
    *   提供连接状态和操作反馈。
    *   内置调试日志查看器。
*   **AI 模型集成:**
    *   支持连接外部 AI 模型 API (例如智谱 AI) 进行 NLQ。
    *   提供 AI 模型连接测试功能。

## 📸 截图

![image](https://github.com/user-attachments/assets/faa3e95e-5639-484c-9dc2-7fc00b1bc93d)

![image](https://github.com/user-attachments/assets/7ec5a6fe-2cda-4184-9dea-cba96b8bafcc)

![image](https://github.com/user-attachments/assets/43604d61-dae8-4573-8791-78bdb05098e5)

![image](https://github.com/user-attachments/assets/53496179-0b8d-4f7f-81d6-f73111de8bfe)

## 📹 详细讲解视频与使用教程

[MySQL AI 查询工具讲解与使用教程](https://www.bilibili.com/video/BV1QRdoYZETh/?spm_id_from=333.1387.homepage.video_card.click&vd_source=26053b834f0ddd4f57b22169d74b6f78)

### 核心模块功能

1. **`app.py`**：
   * Flask 应用主入口
   * 定义 Web 路由和 API 端点
   * 连接前端请求与后端处理逻辑

2. **`config.py`**：
   * 存储 AI 模型 API 密钥和配置
   * 数据库默认连接参数
   * 应用全局设置

3. **`llm_interaction.py`**：
   * 负责与 AI 语言模型的交互
   * 自然语言到 SQL 的转换核心逻辑
   * 处理 AI 响应和解释生成

4. **`db/` 模块**：
   * **`connection.py`**：安全管理数据库连接，处理认证和连接池
   * **`utils.py`**：提供数据库元数据分析，生成表结构信息和样本数据

5. **前端资源**：
   * **`static/js/`**：前端交互逻辑、SQL编辑器、表格展示和可视化
   * **`static/css/`**：样式和主题设置
   * **`templates/`**：HTML页面模板

6. **`utils/` 模块**：
   * **`prompts.py`**：为 AI 模型定义结构化提示模板

## 🔄 工作流程

### 自然语言查询到 SQL 的转换过程

1. **用户输入处理**：
   * 用户在 Web 界面输入自然语言问题
   * 前端通过 AJAX 发送到后端 API

2. **数据库上下文收集**：
   * 系统获取当前数据库的表结构信息（表名、列名、数据类型、约束等）
   * 从相关表中抽取少量样本数据，帮助 AI 理解实际内容格式

3. **上下文构建与 AI 查询**：
   * 将用户问题、数据库结构和样本数据组织成结构化提示
   * 调用 AI 模型（如智谱 AI）API 进行处理
   * 系统对 AI 生成的响应进行解析，提取 SQL 查询语句

4. **SQL 执行与结果处理**：
   * 执行生成的 SQL 查询语句
   * 捕获并处理潜在错误
   * 格式化查询结果为用户友好的表格

5. **结果解释生成**：
   * 将查询结果发送回 AI 模型
   * 生成自然语言解释，帮助用户理解数据含义
   * 将 SQL、结果和解释一起展示给用户

## 💻 技术栈

*   **后端:**
    *   Python
    *   Flask (Python Web 框架)
    *   SQLAlchemy (ORM/DB 连接库)
    *   MySQL Connector Python
    *   智谱 AI SDK (Zhipu AI SDK)
*   **前端:**
    *   HTML5
    *   Tailwind CSS v3
    *   JavaScript (ES6+)
    *   CodeMirror (SQL 编辑器)
    *   Tabulator.js (结果表格)
    *   Vis.js (关系图谱可视化)
    *   Bootstrap Icons (图标)
*   **数据库:**
    *   MySQL

## 🚀 安装与启动

**先决条件:**

*   Python 3.8+
*   pip (Python 包管理器)
*   MySQL 服务器正在运行
*   (可选) Node.js 和 npm (如果需要修改前端资源或进行构建)

**步骤:**

1.  **克隆仓库:**
    ```bash
    git clone https://github.com/guangxiangdebizi/MySQL-ragLLM.git
    cd MySQL-ragLLM
    ```

2.  **创建并激活虚拟环境:**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装后端依赖:**
    ```bash
    pip install -r requirements.txt
    ```
    *(确保 `requirements.txt` 文件包含所有必要的 Python 包，例如 Flask, SQLAlchemy, mysql-connector-python, zhipuai 等)*

4.  **配置:**
    *   **AI API 密钥:** 编辑 `config.py` 文件，填入你的 AI 模型 API 密钥。
      ```python
      # config.py
      AI_API_KEY = "YOUR_ZHIPU_API_KEY" # 替换为你的密钥
      # ... 其他配置
      ```
    *   **(可选) 默认数据库连接:** 你也可以在 `config.py` 或通过环境变量设置默认连接参数。

5.  **启动应用:**
    ```bash
    python app.py
    ```
    *(应用将启动 Flask 服务器)*

6.  **访问应用:**
    在浏览器中打开 `http://127.0.0.1:5000` (或 Flask 运行指定的地址和端口)。

## ⚙️ 配置

### 数据库连接

应用启动后，在左侧的 "数据库配置" 面板中输入你的 MySQL 连接信息：

*   **用户名:** 数据库用户名 (例如 `root`)
*   **密码:** 数据库密码
*   **主机地址:** 数据库服务器地址 (例如 `localhost` 或 IP 地址)
*   **端口:** 数据库服务器端口 (默认为 `3306`)
*   **数据库:** 连接成功后，下拉列表会显示可用的数据库，选择一个进行操作。

使用 "测试连接" 按钮验证配置是否正确。配置可以 "保存" 到浏览器本地存储，并在下次访问时 "加载"。

### AI 模型

*   **API Key:** AI 模型 (如智谱 AI) 的 API Key 需要在后端的 `config.py` 文件中设置。请参考 `config.py.example` (如果提供) 或直接修改 `config.py`。
    ```python
    # config.py
    AI_API_KEY = "YOUR_API_KEY"
    ```
*   **测试连接:** 在配置面板中，可以使用 "测试AI模型连接" 按钮检查后端是否能成功与 AI 服务通信。

## 📖 使用指南

1.  **连接数据库:** 首先在左侧面板配置并测试数据库连接，然后选择一个数据库。
2.  **自然语言查询:**
    *   切换到 "SQL查询" 标签页。
    *   在 "自然语言查询" 面板的文本框中输入你的问题 (中文或英文)。
    *   点击 "提交自然语言查询" 按钮或按 `Ctrl+Enter`。
    *   等待 AI 处理，下方将显示生成的 SQL、查询结果表格和 AI 的解释。
3.  **直接 SQL 查询:**
    *   在 "直接 SQL 查询" 面板的编辑器中输入你的 SQL 语句。
    *   点击 "执行 SQL" 按钮。
    *   下方将显示你输入的 SQL 和查询结果表格 (或操作成功/失败信息)。
    *   使用 "清空 SQL 输入" 按钮清除编辑器内容。
4.  **浏览数据库结构:**
    *   切换到 "数据库结构" 标签页。
    *   点击 "加载数据库结构" 按钮。
    *   面板将显示数据库中的所有表及其列信息。
5.  **查看表关系:**
    *   切换到 "表关系图谱" 标签页。
    *   点击 "加载关系图谱" 按钮。
    *   面板将显示一个交互式的图谱，展示表之间的外键关系。
6.  **查看查询历史:**
    *   在 "SQL查询" 标签页的结果区域下方，找到 "查询历史" 部分 (初始可能隐藏，或通过按钮切换)。
    *   历史记录会列出你之前的查询。
    *   点击 "加载" 按钮可以重新载入该查询的 SQL、结果和解释。
    *   点击 "清除历史" 可清空所有记录。
7.  **导出结果:**
    *   在查询结果表格上方 (或附近)，找到导出按钮 (如果实现)，可以选择导出为 CSV 或 JSON 格式。
8.  **切换主题:**
    *   点击左上角的月亮/太阳图标切换深色和浅色模式。

## 🤝 贡献

欢迎提出 Issue 和 Pull Request。

1.  Fork 本仓库
2.  创建你的 Feature 分支 (`git checkout -b feature/AmazingFeature`)
3.  提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  打开一个 Pull Request

## 📞 联系方式

* **邮箱：** [guangxiangdebizi@gmail.com](mailto:guangxiangdebizi@gmail.com)
* **领英：** [陈星宇](https://www.linkedin.com/in/星宇-陈-b5b3b0313/)
* **GitHub：** [guangxiangdebizi](https://github.com/guangxiangdebizi/)

## 📄 许可证

本项目采用 [MIT](https://opensource.org/licenses/MIT) 许可证。 
