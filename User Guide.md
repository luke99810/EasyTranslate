# EasyTranslate 使用指南

## 1. 项目介绍

EasyTranslate 是一个专为学术研究人员设计的PDF翻译工具，支持将英文学术论文翻译成中文，保持原文排版和公式结构，提供双语对照阅读体验。

### 核心功能
- 📁 **PDF上传**：支持上传PDF文件，自动分析页面结构
- 🌐 **多引擎翻译**：集成DeepL、Google、OpenAI等多种翻译引擎
- 🔍 **双语对照**：提供原文和译文的并排对照阅读
- 📝 **公式保护**：智能识别和保护LaTeX公式，避免翻译破坏
- 📄 **导出功能**：支持导出翻译后的PDF或Word文档
- 🔧 **自定义设置**：可调整翻译引擎、语言、字体大小等

## 2. 环境要求

### Docker部署（推荐）
- Docker & Docker Compose

### 本地开发
- Node.js 16+
- Python 3.10+

## 3. 启动方法

### 方法一：使用Docker Compose部署

1. **进入项目目录**：
   ```bash
   cd c:\Users\宿心\WorkBuddy\EasyTranslate\paper-translate
   ```

2. **启动服务**：
   ```bash
   docker-compose up -d
   ```

3. **查看服务状态**：
   ```bash
   docker-compose ps
   ```

4. **访问服务**：
   - 前端：http://localhost
   - 后端API：http://localhost:8000/api

### 方法二：本地开发启动

#### 前端启动
1. **进入前端目录**：
   ```bash
   cd c:\Users\宿心\WorkBuddy\EasyTranslate\paper-translate\frontend
   ```

2. **安装依赖**：
   ```bash
   npm install
   ```

3. **启动开发服务器**：
   ```bash
   npm run dev
   ```

#### 后端启动
1. **进入后端目录**：
   ```bash
   cd c:\Users\宿心\WorkBuddy\EasyTranslate\paper-translate\backend
   ```

2. **创建虚拟环境**：
   ```bash
   python -m venv venv
   ```

3. **激活虚拟环境**：
   ```bash
   # Windows
   venv\Scripts\activate
   ```

4. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

5. **启动开发服务器**：
   ```bash
   uvicorn app.main:app --reload
   ```

## 4. 使用流程

### 步骤1：上传PDF文件

1. **打开应用**：访问 http://localhost（Docker部署）或前端开发服务器地址（本地开发）
2. **上传文件**：点击首页的"上传PDF"按钮，选择要翻译的学术论文
3. **等待分析**：系统会自动分析PDF文件，提取页面结构和内容

### 步骤2：配置翻译参数

1. **选择翻译引擎**：在翻译配置页面，选择DeepL、Google或OpenAI
2. **输入API Key**：根据所选翻译引擎，输入对应的API Key
   - DeepL：https://www.deepl.com/pro-api
   - Google Cloud Translation：https://cloud.google.com/translate
   - OpenAI：https://platform.openai.com/api-keys
3. **选择语言**：默认源语言为英语，目标语言为中文
4. **开始翻译**：点击"开始翻译"按钮，系统会开始处理翻译任务

### 步骤3：阅读翻译结果

1. **查看双语对照**：翻译完成后，系统会自动跳转到阅读页面
2. **调整布局**：可选择水平或垂直布局查看原文和译文
3. **同步滚动**：启用同步滚动功能，方便对照阅读
4. **调整字体**：根据需要调整字体大小

### 步骤4：导出翻译结果

1. **点击导出**：在阅读页面顶部工具栏，点击"导出"按钮
2. **选择格式**：选择导出为PDF或Word格式
3. **下载文件**：等待导出完成后，点击下载按钮保存文件

## 5. 功能详解

### 5.1 双语阅读器

- **布局模式**：水平分割（左右）或垂直分割（上下）
- **同步滚动**：原文和译文保持同步滚动
- **字体调整**：可调整字体大小，适应不同阅读需求
- **页面导航**：快速跳转到指定页面

### 5.2 翻译引擎选择

| 翻译引擎 | 特点 | 适用场景 |
|---------|------|----------|
| DeepL | 学术翻译质量高，术语准确 | 学术论文翻译 |
| Google | 翻译速度快，支持多种语言 | 快速翻译 |
| OpenAI | 上下文理解能力强，翻译流畅 | 复杂文档翻译 |

### 5.3 公式处理

- **自动识别**：智能识别LaTeX公式
- **公式保护**：翻译过程中保持公式结构不变
- **格式保持**：导出时保持公式的原始格式

## 6. 常见问题

### 6.1 翻译引擎API Key获取

- **DeepL**：注册DeepL Pro账号，在API设置中获取
- **Google Cloud Translation**：创建Google Cloud项目，启用翻译API，生成API Key
- **OpenAI**：登录OpenAI平台，在API密钥页面创建新的API Key

### 6.2 支持的文件格式

- 仅支持PDF格式文件
- 建议文件大小不超过50MB
- 建议页数不超过100页

### 6.3 翻译质量

- 翻译质量取决于所选的翻译引擎和API Key的权限等级
- 建议使用DeepL Pro或OpenAI GPT-4以获得最佳翻译效果
- 对于专业术语较多的论文，可能需要手动调整部分翻译结果

### 6.4 导出文件大小

- 导出的PDF文件可能比原文件大，因为包含了双语内容
- 对于大型文档，导出过程可能需要较长时间

## 7. 故障排除

### 7.1 服务启动失败

- **Docker部署**：检查Docker是否正常运行，查看容器日志
  ```bash
  docker-compose logs
  ```

- **本地开发**：检查Node.js和Python版本是否符合要求，查看终端错误信息

### 7.2 翻译失败

- 检查API Key是否正确
- 检查网络连接是否正常
- 检查翻译引擎是否有API调用限制

### 7.3 导出失败

- 检查文件大小是否超过限制
- 检查系统存储空间是否充足
- 尝试重新导出或选择其他格式

### 7.4 页面加载缓慢

- 对于大型PDF文件，首次加载可能需要较长时间
- 尝试关闭其他浏览器标签页或应用程序
- 检查网络连接速度

## 8. 技术支持

如果遇到任何问题，请联系项目维护者或查看项目文档获取更多信息。

---

**版本**：P0
**最后更新**：2026-04-12