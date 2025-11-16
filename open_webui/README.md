# open_webui
用open-webui做rag測試，自己環境建好可以直接用自己的

### 安裝必要套件
```
pip install open-webui
pip uninstall torch torchvision torchaudio -y #避免套件衝突
```

### 開啟open webui server
```
open-webui serve --host 127.0.0.1 --port 3000
```

在管理員控制台>設定>連線，在OpenAI API新增
> http://localhost:8000/v1

聊天時記得將模型切為"ncu-rag-ollama"