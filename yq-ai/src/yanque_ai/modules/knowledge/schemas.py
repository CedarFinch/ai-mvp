"""知识库管理接口数据模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeBaseCreateRequest(BaseModel):
    """Java 创建知识库后，请求 Python 初始化 Milvus Collection。"""

    code: str = Field(description="知识库编码，用于生成 Collection 名称")
    name: str = Field(description="知识库名称")
    description: str | None = Field(default=None, description="知识库说明")


class KnowledgeBaseCreateResponse(BaseModel):
    """Milvus Collection 初始化结果。"""

    collection_name: str
    dense_vector_field: str = "dense_vector"
    sparse_vector_field: str = "sparse_vector"


class KnowledgeBaseDeleteRequest(BaseModel):
    """Java 删除知识库前，请求 Python 删除对应 Milvus Collection。"""

    code: str = Field(description="知识库编码，用于生成 Collection 名称")


class KnowledgeBaseDeleteResponse(BaseModel):
    """Milvus Collection 删除结果。"""

    collection_name: str
    deleted: bool


class KnowledgeDocumentIndexRequest(BaseModel):
    """Java 请求 Python 下载、切分并入库知识库文档。"""

    knowledge_base_id: int = Field(description="知识库ID")
    knowledge_base_code: str = Field(description="知识库编码，对应 Milvus Collection 名称")
    document_id: int = Field(description="文档ID")
    document_code: str = Field(description="文档编码")
    document_name: str = Field(description="文档名称")
    document_version: int = Field(description="文档版本号")
    object_key: str = Field(description="TOS对象Key")
    download_url: str = Field(description="TOS预签名下载地址")
    file_type: Literal["md", "json"] = Field(default="md", description="文件类型")
    chunk_strategy: Literal["MARKDOWN", "NONE", "BY_ITEM"] = Field(
        default="MARKDOWN",
        description="切分策略：MARKDOWN 按 Markdown 结构切分，NONE 整篇入库，BY_ITEM 按 JSON 数组元素入库",
    )
    file_size: int | None = Field(default=None, description="文件大小，单位字节")


class KnowledgeDocumentIndexResponse(BaseModel):
    """知识库文档入库结果。"""

    collection_name: str
    chunk_count: int


class KnowledgeDocumentChunkQueryRequest(BaseModel):
    """Java 请求 Python 查询某个文档的 chunk 列表。"""

    knowledge_base_code: str = Field(description="知识库编码，对应 Milvus Collection 名称")
    document_code: str = Field(description="文档编码")
    document_version: int = Field(description="文档版本号")
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")


class KnowledgeDocumentChunkItem(BaseModel):
    """Milvus 中单个文档 chunk 的展示信息。"""

    chunk_index: int
    content_preview: str
    word_count: int
    char_count: int


class KnowledgeDocumentChunkQueryResponse(BaseModel):
    """文档 chunk 分页查询结果。"""

    collection_name: str
    records: list[KnowledgeDocumentChunkItem]


class KnowledgeDocumentChunkDetailRequest(BaseModel):
    """Java 请求 Python 查询某个 chunk 的完整内容。"""

    knowledge_base_code: str = Field(description="知识库编码，对应 Milvus Collection 名称")
    document_code: str = Field(description="文档编码")
    document_version: int = Field(description="文档版本号")
    chunk_index: int = Field(ge=0, description="chunk序号")


class KnowledgeDocumentChunkDetailResponse(BaseModel):
    """文档 chunk 完整内容查询结果。"""

    collection_name: str
    chunk_index: int
    content: str
    word_count: int
    char_count: int


class KnowledgeDocumentDeleteRequest(BaseModel):
    """Java 请求 Python 删除某个文档的向量数据。"""

    knowledge_base_code: str = Field(description="知识库编码，对应 Milvus Collection 名称")
    document_code: str = Field(description="文档编码")


class KnowledgeDocumentDeleteResponse(BaseModel):
    """文档向量删除结果。"""

    collection_name: str
    deleted: bool


class KnowledgeRecallRequest(BaseModel):
    """Java 请求 Python 执行知识库召回测试。"""

    knowledge_base_code: str = Field(description="知识库编码，对应 Milvus Collection 名称")
    query: str = Field(min_length=1, description="召回查询文本")
    mode: str = Field(default="HYBRID", description="SEMANTIC 语义，KEYWORD 关键字，HYBRID 混合")
    top_k: int = Field(default=5, ge=1, le=20, description="召回数量")


class KnowledgeRecallItem(BaseModel):
    """单条召回结果。"""

    rank: int
    score: float
    document_code: str
    document_version: int
    chunk_index: int
    content: str
    content_preview: str
    word_count: int


class KnowledgeRecallResponse(BaseModel):
    """知识库召回测试结果。"""

    query: str
    mode: str
    top_k: int
    records: list[KnowledgeRecallItem]


class KnowledgeQaStreamRequest(BaseModel):
    """Java 请求 Python 执行知识库问答测试。"""

    knowledge_base_code: str = Field(description="知识库编码，对应 Milvus Collection 名称")
    question: str = Field(min_length=1, description="问答测试问题")
    recall_mode: str = Field(default="HYBRID", description="SEMANTIC 语义，KEYWORD 关键字，HYBRID 混合")
    top_k: int = Field(default=5, ge=1, le=20, description="召回数量")
