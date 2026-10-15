"""Milvus 稠密向量与 BM25 混合检索公共能力。"""

from __future__ import annotations

from typing import Protocol

from llama_index.embeddings.openai import OpenAIEmbedding
from pymilvus import AnnSearchRequest, DataType, Function, FunctionType, MilvusClient, WeightedRanker
from pymilvus.exceptions import MilvusException


class HybridStoreConfig(Protocol):
    """知识库与视频素材共同依赖的向量配置。"""

    uri: str
    token: str | None
    db_name: str
    dense_dim: int
    dense_metric_type: str
    sparse_metric_type: str
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_batch_size: int


class HybridSearchStore:
    """封装 Collection 共用的向量字段、索引、Embedding 和混合召回。"""

    def __init__(self, config: HybridStoreConfig) -> None:
        self.config = config

    def add_vector_fields(self, schema) -> None:
        """向业务 Schema 添加检索文本、稠密向量和 BM25 稀疏向量。"""
        schema.add_field(
            "text",
            DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
            analyzer_params={"type": "chinese"},
        )
        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=self.config.dense_dim)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
        schema.add_function(
            Function(
                name="text_bm25_function",
                function_type=FunctionType.BM25,
                input_field_names=["text"],
                output_field_names=["sparse_vector"],
            )
        )

    def prepare_index_params(self):
        """创建知识库和视频素材共用的 Dense 与 BM25 索引参数。"""
        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_type="AUTOINDEX",
            metric_type=self.config.dense_metric_type,
        )
        index_params.add_index(
            field_name="sparse_vector",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type=self.config.sparse_metric_type,
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75,
            },
        )
        return index_params

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量生成入库文本的稠密向量。"""
        return self.embedding_model().get_text_embedding_batch(texts)

    def search(
        self,
        collection_name: str,
        query: str,
        mode: str,
        top_k: int,
        output_fields: list[str],
        filter_expression: str = "",
    ) -> list[dict]:
        """按语义、关键词或混合模式召回业务记录。"""
        client = self.client()
        normalized_mode = mode.upper()
        if normalized_mode == "SEMANTIC":
            results = client.search(
                collection_name=collection_name,
                data=[self.embedding_model().get_query_embedding(query)],
                anns_field="dense_vector",
                filter=filter_expression,
                search_params={"metric_type": self.config.dense_metric_type},
                limit=top_k,
                output_fields=output_fields,
            )
        elif normalized_mode == "KEYWORD":
            results = client.search(
                collection_name=collection_name,
                data=[query],
                anns_field="sparse_vector",
                filter=filter_expression,
                search_params={"metric_type": self.config.sparse_metric_type},
                limit=top_k,
                output_fields=output_fields,
            )
        elif normalized_mode == "HYBRID":
            dense_request = AnnSearchRequest(
                data=[self.embedding_model().get_query_embedding(query)],
                anns_field="dense_vector",
                param={"metric_type": self.config.dense_metric_type},
                limit=top_k,
                filter=filter_expression,
            )
            sparse_request = AnnSearchRequest(
                data=[query],
                anns_field="sparse_vector",
                param={"metric_type": self.config.sparse_metric_type},
                limit=top_k,
                filter=filter_expression,
            )
            results = client.hybrid_search(
                collection_name=collection_name,
                reqs=[dense_request, sparse_request],
                ranker=WeightedRanker(0.7, 0.3),
                limit=top_k,
                output_fields=output_fields,
            )
        else:
            raise ValueError("召回模式不合法")
        return results[0] if results else []

    def client(self) -> MilvusClient:
        """创建 Milvus 客户端。"""
        try:
            if self.config.token:
                return MilvusClient(
                    uri=self.config.uri,
                    token=self.config.token,
                    db_name=self.config.db_name,
                )
            return MilvusClient(uri=self.config.uri, db_name=self.config.db_name)
        except MilvusException as exc:
            raise RuntimeError(
                f"Milvus 连接失败，请检查 MILVUS_URI={self.config.uri} 是否可访问"
            ) from exc

    def embedding_model(self) -> OpenAIEmbedding:
        """创建百炼 OpenAI 兼容 Embedding 模型。"""
        if not self.config.embedding_api_key:
            raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法生成稠密向量")
        return OpenAIEmbedding(
            model_name=self.config.embedding_model,
            api_key=self.config.embedding_api_key,
            api_base=self.config.embedding_base_url,
            embed_batch_size=self.config.embedding_batch_size,
        )
