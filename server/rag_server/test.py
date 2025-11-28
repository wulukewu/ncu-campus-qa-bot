# 2. 修改您的程式碼
from langchain_huggingface import HuggingFaceEmbeddings

# 替換原本的 OpenAI embeddings
emb = HuggingFaceEmbeddings(
    model_name="shibing624/text2vec-base-chinese",  # 中文優化模型
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 測試
result = emb.embed_query("測試")
print(f"成功! 向量維度: {len(result)}")