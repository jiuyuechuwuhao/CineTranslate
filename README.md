# 🎬 CineTranslate - 影视译名通

> **专业级影视剧英文名查找工具 | The Ultimate Movie Name Translator**
>
> 基于 TMDB 和 豆瓣 双平台大数据，专为中国影视海外传播学者、影视创作者及影迷朋友们打造的精准译名解决方案。

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Framework-Flask-green.svg?style=flat-square&logo=flask&logoColor=white)
![Vercel](https://img.shields.io/badge/Deployment-Vercel-black.svg?style=flat-square&logo=vercel&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-orange.svg?style=flat-square)

---

## 📖 项目简介 (Introduction)

**CineTranslate** 解决了影视工作流中的一个痛点：**如何快速、准确地找到中文影视剧对应的官方英文名称？**

传统的搜索方式往往需要在多个网站之间切换，效率低且结果参差不齐。本工具通过智能算法，同时检索 **TMDB (全球最大影视数据库)** 和 **豆瓣电影**，可以一次识别多个中文影视片目，进行批量化检索并自动比对结果，为您推荐最准确的官方英文译名。

## 🚀 在线演示 (Demo)

👉 **[点击这里访问 CineTranslate 在线版](https://cine-translate.vercel.app/)**


---

## 📂 项目文件结构 (File Structure)

以下是本项目核心文件的功能说明，帮助开发者快速理解代码架构：

- `app.py`Flask 主程序入口，负责启动 Web 服务器、处理 API 请求和页面路由。
- `find_english_names.py`核心搜索引擎，封装了 TMDB 和 豆瓣 的爬虫逻辑与数据匹配算法。
- `movie_name_extractor.py`智能提取模块，用于处理自然语言文本，识别其中的影视剧名称（使用了 Jieba 分词）。
- `requirements.txt`依赖清单（精简版），记录了项目运行所需的 Python 库，适配 Vercel 环境。
- `vercel.json`Vercel 部署配置文件，定义了 Serverless 函数的入口和运行环境。
- `templates/`前端模板文件夹，包含 `index.html` 等网页源码。
- `static/`
  静态资源文件夹，存放网站图标、CSS 样式等文件。

---

## ✨ 核心功能 (Features)

- 🔍 **双核极速搜索**：

  - 同时聚合 TMDB 和 豆瓣 数据，确保冷门佳片也能找到。
  - 智能过滤无关结果，只展示最匹配的条目。
- 🧠 **智能推荐算法**：

  - 自动对比双平台数据，优先推荐 TMDB 官方英文名。
  - 当官方无结果时，智能回退至豆瓣译名，并标注来源。
- 📊 **专业数据导出**：

  - 支持 **CSV**：保留完整元数据（链接、备注），适合表格整理。
  - 支持 **TXT**：简洁格式，适合直接复制到笔记或剪辑软件中。
  - 支持 **JSON**：适合开发者进行二次开发。
- 🎨 **现代化 UI 设计**：

  - 响应式布局，完美适配 手机、平板、PC 桌面。
  - 支持 🎬 手动输入、📋 智能提取、📂 文件导入。

---

## ⚡️ 快速部署 (Deployment)

本项目已针对 **Vercel** 进行深度优化，支持 **零配置** 一键部署。

### 方法一：使用 GitHub (推荐)

1. **Fork** 本仓库到你的 GitHub 账号。
2. 登录 [Vercel](https://vercel.com) 并点击 **"Add New Project"**。
3. 选择刚才 Fork 的仓库，点击 **Import**。
4. 直接点击 **Deploy** (无需配置环境变量)。
5. 等待 30 秒，你的专属网站即刻上线！

### 方法二：本地运行 (Local Development)

如果你想在本地电脑上运行或开发：

```bash
# 1. 克隆项目
git clone https://github.com/jiuyuechuwuhao/CineTranslate.git

# 2. 进入目录
cd CineTranslate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python app.py
```

启动后，打开浏览器访问 http://localhost:8084 即可。
📄 开源协议 (License)
本项目采用 MIT License 开源协议。
您可以自由地使用、修改和分发本项目，但在重新发布时请保留原作者的版权声明。

<div align="center">
Made with ❤️ by <a href="https://github.com/jiuyuechuwuhao">jiuyuechuwuhao</a>
</div>
