# AI 商品图生成工具

上传商品实拍原图(可多张) → 调用即梦(火山引擎)云端 API → 生成 5 张 800×800 主图 + 1 张 AI 详情页 + 1 张九宫格详情图(宽 800、高 ≤1200)→ 按日期目录保存 → 浏览器预览下载。

面向 1688 TO B 定制店铺(纸罐/包装行业)的商品图生产场景,单人使用、免登录。

---

## 功能

- 上传 1~9 张商品实拍原图,全部作为 AI 参考图(多参考图更精准)
- 自动生成 **5 张主图**(800×800,每张独立提示词,默认取自 ai-images.txt 流水线要求):
  1. 白底实拍图(商品提取 API 抠图,符合 1688 白底规范)
  2. 工艺实力细节图(5:5 分栏,微距工艺)
  3. 全行业适配图(3×3 九宫格 9 款式)
  4. OEM 定制服务图(4 步流程图)
  5. 平台合规纯白底图(无文字)
- 自动生成 **2 张详情图**:
  1. AI 生成 6 区域 OEM 详情页(竖版长图,宽 800)
  2. 3×3 九宫格(本地 Pillow 拼接,由主图+原图拼格)
- **提示词管理**:5 主图 + 2 详情图各自独立编辑,保存到服务器 `prompts.json`,重启不丢
- 重新生成:页面刷新后可再次上传重跑
- 按日期目录归档:`outputs/YYYY-MM-DD/<task_id>/主图/、详情图/`
- 异步生成:提交后前端轮询进度(约 1-3 分钟)

## API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 多文件 `files`(1~9 张)+ `prompts`(JSON 字符串),返回 `task_id` |
| `/api/task/{id}` | GET | 轮询任务状态与结果 |
| `/api/prompts` | GET | 读取提示词 `{"main": [5], "detail": [2]}` |
| `/api/prompts` | POST | 保存提示词(同结构 JSON body) |
| `/api/tasks` | GET | 历史任务列表 |

## 技术栈

- Python 3.10+ / FastAPI / uvicorn
- Pillow(缩放、白底合成、九宫格拼接)
- volcengine SDK(即梦 API,AK/SK 签名)
- 原生 HTML/CSS/JS 前端(无框架)

## 快速开始

```bash
cd /home/musk/ai-image-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # 国内可用清华源: -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置凭据
cp .env.example .env
# 编辑 .env,填入 JIMENG_ACCESS_KEY / JIMENG_SECRET_KEY(或 ARK_API_KEY)

# 启动
./run.sh
# 或: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://<服务器IP>:8000`。

## 部署实况(2026-08-02,Debian 12 + 宝塔 + systemd)

> 实际部署环境:服务器 192.168.1.41(主机名 msi,Python 3.13.5),宝塔 /www/wwwroot/ai-image-studio。
> ⚠️ **端口说明**:8000 已被服务器上既有项目 api-football 占用,本项目实际运行在 **8001**。
> 访问地址:`http://192.168.1.41:8001`。

- 代码来源:GitHub 私有仓库 `cl329267776/ai-image-studio`(git clone)
- 进程守护:systemd 服务 `ai-image-studio`(User=www,开机自启)
- 运维命令:
  ```bash
  systemctl restart ai-image-studio      # 重启
  journalctl -u ai-image-studio -f       # 看日志
  systemctl status ai-image-studio       # 状态
  ```
- 防火墙:UFW 已放行 8001/tcp
- .env 位置:`/www/wwwroot/ai-image-studio/.env`(AK/SK 填入后 `systemctl restart ai-image-studio`)
- 更新代码:服务器 `/www/wwwroot/ai-image-studio` 内 `git pull`,然后重启服务

## 配置说明(.env)

| 变量 | 说明 | 必填 |
|------|------|------|
| `API_PROVIDER` | 通道选择:`jimeng`(即梦电商 API,默认)或 `ark`(方舟 Seedream) | 否 |
| `JIMENG_ACCESS_KEY` | 火山引擎 AccessKey ID | 选填(选 jimeng 时必填) |
| `JIMENG_SECRET_KEY` | 火山引擎 Secret Access Key | 选填(选 jimeng 时必填) |
| `ARK_API_KEY` | 方舟 API Key(OpenAI 兼容) | 选填(选 ark 时必填) |
| `PORT` | 服务端口,默认 8000 | 否 |

### 凭据获取

**即梦通道(推荐,0.2~0.22 元/张):**
1. 登录 https://console.volcengine.com(需实名认证)
2. 右上角头像 → 「API 访问密钥」→ 创建密钥
3. 得到 AccessKey ID + Secret Access Key,填入 .env
4. 首次使用在「智能视觉控制台」开通即梦 AI 服务(有免费试用额度)

**方舟通道(备选,0.3~0.6 元/张):**
1. 登录 https://console.volcengine.com/ark
2. 左侧「API Key 管理」→ 创建 API Key
3. 填入 .env 的 `ARK_API_KEY`,并把 `API_PROVIDER` 改为 `ark`

## API 说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/upload` | POST | 上传原图(multipart:file + custom_prompt),返回 `{task_id}` |
| `/api/task/{task_id}` | GET | 查询任务状态:`pending/generating/done/partial/failed`,含图片文件名列表 |
| `/api/tasks` | GET | 历史任务列表 |
| `/outputs/{date}/{task_id}/{file}` | GET | 预览/下载生成图 |

### 任务状态

- `pending` 排队中 → `generating` AI 生成中 → `done` 全部成功 / `partial` 部分成功(看 error 字段)/ `failed` 失败(error 字段含原因)

## 部署到宝塔面板(Debian 12)

### 方式一:Python 项目管理器(推荐,可视化)

1. **上传代码**:宝塔「文件」→ 上传 `/home/musk/ai-image-studio` 整个项目到 `/www/wwwroot/ai-image-studio`(或用 git 拉取)

2. **安装 Python 项目管理器**:宝塔「软件商店」→ 搜索「Python 项目管理器」→ 安装

3. **添加项目**:
   - 项目名称:`ai-image-studio`
   - 项目路径:`/www/wwwroot/ai-image-studio`
   - Python 版本:3.11(或服务器已有版本)
   - 启动方式:`uvicorn`
   - 启动文件:`app/main.py`
   - 启动参数:`--host 0.0.0.0 --port 8000`
   - 安装依赖:勾选「安装模块依赖」(读取 requirements.txt)

4. **配置 .env**:宝塔文件管理打开 `/www/wwwroot/ai-image-studio/.env`,填入真实凭据(从 .env.example 复制)

5. **启动项目**:项目管理器列表 → 该项目 → 启动

6. **验证**:服务器终端 `curl -s http://127.0.0.1:8000/ | head -3`,能看到 HTML 即成功

### 方式二:systemd 服务(无 Python 管理器时)

```bash
# 服务器终端
cd /www/wwwroot/ai-image-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入凭据
```

创建服务文件 `/etc/systemd/system/ai-image-studio.service`:

```ini
[Unit]
Description=AI Image Studio
After=network.target

[Service]
WorkingDirectory=/www/wwwroot/ai-image-studio
ExecStart=/www/wwwroot/ai-image-studio/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
User=www

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-image-studio
systemctl status ai-image-studio
```

### Nginx 反向代理(可选,推荐)

宝塔「网站」→「添加站点」→ 反向代理指向 `http://127.0.0.1:8000`,或手动配置:

```nginx
server {
    listen 80;
    server_name your-domain.com;      # 或服务器 IP
    client_max_body_size 20m;         # 允许上传大图

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

放行端口:宝塔「安全」→ 放行 8000(或 80/443,取决于访问方式)。

## 目录结构

```
ai-image-studio/
├── app/
│   ├── main.py            # FastAPI 入口与路由
│   ├── config.py          # 配置加载(.env)
│   ├── storage.py         # 日期目录存储
│   ├── api/
│   │   ├── jimeng_client.py   # 即梦 API 客户端(AK/SK,异步提交+轮询)
│   │   ├── ark_client.py      # 方舟 Seedream 备选(API Key,同步)
│   │   └── factory.py         # 双通道适配器
│   ├── services/
│   │   ├── generate.py        # 生成编排(主图+详情图)
│   │   └── postprocess.py     # Pillow 后处理(缩放/九宫格)
│   └── static/                # 前端单页(index.html/style.css/app.js)
├── outputs/               # 生成结果:outputs/YYYY-MM-DD/<task_id>/主图/、详情图/
├── uploads/               # 上传暂存(当前直接存 outputs 任务目录)
├── requirements.txt
├── .env.example           # 配置模板
├── .env                   # 实际配置(不入库)
├── run.sh                 # 启动脚本
└── README.md
```

## 常见问题

**Q: 生成失败,错误是 InvalidCredential?**
A: AK/SK 无效或未开通服务。检查 .env 填写是否正确、火山引擎是否实名认证、智能视觉控制台是否已开通即梦服务。

**Q: 5 张主图是串行生成,会不会很慢?**
A: 即梦平台默认并发 1~2,单商品约 1-3 分钟。如需提速,可在火山引擎控制台增购并发(付费),或切换 `API_PROVIDER=ark` 用方舟通道(同步返回)。

**Q: 生成的图能直接传 1688 吗?**
A: 第 1 张白底图符合 1688 主图规范(800×800 白底、主体居中)。但平台要求「实拍」,AI 风格化主图建议用于详情页/活动图,正式上架前请人工审核。文字/logo 请后期用设计工具添加(AI 生成文字易乱码)。

**Q: 重启服务后任务历史丢失?**
A: 任务状态存内存(单用户够用),生成的文件仍在磁盘 outputs/ 目录,可通过 /api/tasks 按目录扫描找回。

**Q: 图片上传大小限制?**
A: 直接访问 8000 端口无限制;经 Nginx 反代需设置 `client_max_body_size 20m`。

## 成本参考

- 即梦通道:背景替换 0.2 元/张、商品提取 0.22 元/张;单商品(1 提取 + 4 背景替换 + 2 次详情拼图)约 **1.3 元**(详情拼图为本地 Pillow 处理,不额外计费)
- 方舟通道:Seedream 5.0 pro 0.3~0.6 元/张
- 免费试用额度 200 次(即梦),可先跑通全流程再付费
