# MoJingStudio

MoJingStudio 是一个基于 PySide6 的桌面工作台，用于管理视频/图片生成任务、素材引用、云端任务查询和生成结果归档。

## 快速开始

1. 安装 Python 依赖：

```powershell
pip install -r requirements.txt
```

2. 启动应用：

```powershell
python run_mojingstudio_modular.py
```

3. 首次运行后，在应用内「管线设置」填写自己的 API Key、Endpoint 和可选 TOS 上传配置。

## 配置说明

仓库内只保留了模板配置：

- `data/config/config.example.json`
- `data/config/model_profiles.example.json`
- `data/config/persona_library.json`
- `data/config/prompt_library.json`

真实的 `data/config/config.json` 会包含个人 API Key、TOS 密钥、本地输出目录等信息，已被 `.gitignore` 排除，请不要提交。

## 不应提交的内容

- `outputs/` 生成结果
- `__pycache__/` Python 缓存
- `data/config/config.json` 个人配置
- API Key、TOS AccessKey、SecretKey
- 本地测试视频、图片、音频素材
