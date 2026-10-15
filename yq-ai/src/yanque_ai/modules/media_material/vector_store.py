"""视频素材 Milvus Collection 与混合检索。"""

from __future__ import annotations

from pymilvus import DataType, MilvusClient

from ..knowledge.hybrid_store import HybridSearchStore
from ..knowledge.vector_store import MilvusKnowledgeConfig
from .schemas import MaterialIndexItem, MaterialRecallRequest


class MediaMaterialVectorStore:
    """一条视频素材对应一条向量记录，不复用文档 chunk 字段。"""

    OUTPUT_FIELDS = [
        "material_id",
        "video_id",
        "clip_type",
        "duration_ms",
        "tags",
        "speakers",
        "text",
    ]

    def __init__(self, config: MilvusKnowledgeConfig) -> None:
        self.hybrid_store = HybridSearchStore(config)

    def create_collection(self, collection_name: str) -> None:
        """创建视频素材专用 Collection；已存在时校验字段。"""
        client = self.hybrid_store.client()
        if client.has_collection(collection_name=collection_name):
            self._validate_schema(client, collection_name)
            return

        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
        schema.add_field("material_id", DataType.INT64)
        schema.add_field("video_id", DataType.INT64)
        schema.add_field("task_id", DataType.INT64)
        schema.add_field("clip_type", DataType.VARCHAR, max_length=32)
        schema.add_field("duration_ms", DataType.INT64)
        schema.add_field(
            "tags",
            DataType.ARRAY,
            element_type=DataType.VARCHAR,
            max_capacity=8,
            max_length=100,
        )
        schema.add_field(
            "speakers",
            DataType.ARRAY,
            element_type=DataType.VARCHAR,
            max_capacity=8,
            max_length=64,
        )
        self.hybrid_store.add_vector_fields(schema)
        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=self.hybrid_store.prepare_index_params(),
        )

    def replace_task_materials(
        self,
        collection_name: str,
        task_id: int,
        materials: list[MaterialIndexItem],
    ) -> int:
        """按任务覆盖索引；失败重试时重复调用也不会产生重复数据。"""
        self.create_collection(collection_name)
        client = self.hybrid_store.client()
        client.delete(collection_name=collection_name, filter=f"task_id == {task_id}")
        if not materials:
            return 0

        texts = [self._build_retrieval_text(material) for material in materials]
        embeddings = self.hybrid_store.embed_documents(texts)
        rows = [
            {
                "id": f"material_{material.material_id}",
                "material_id": material.material_id,
                "video_id": material.video_id,
                "task_id": task_id,
                "clip_type": material.clip_type,
                "duration_ms": material.duration_ms,
                "tags": material.tags,
                "speakers": material.speakers,
                "text": texts[index],
                "dense_vector": embeddings[index],
            }
            for index, material in enumerate(materials)
        ]
        client.upsert(collection_name=collection_name, data=rows)
        return len(rows)

    def recall(
        self,
        collection_name: str,
        request: MaterialRecallRequest,
    ) -> list[dict]:
        """带来源、类型、时长和说话人条件执行视频素材召回。"""
        client = self.hybrid_store.client()
        if not client.has_collection(collection_name=collection_name):
            raise RuntimeError(f"Milvus Collection {collection_name} 不存在")
        hits = self.hybrid_store.search(
            collection_name,
            request.query.strip(),
            request.mode,
            request.top_k,
            self.OUTPUT_FIELDS,
            self._build_filter(request),
        )
        return [self._to_recall_item(index + 1, hit) for index, hit in enumerate(hits)]

    def _build_retrieval_text(self, material: MaterialIndexItem) -> str:
        """只拼接可检索语义；不包含 object_key 或临时播放 URL。"""
        return "\n".join(
            [
                f"标题：{material.title}",
                f"摘要：{material.summary}",
                f"核心观点：{material.core_viewpoint}",
                f"素材类型：{material.clip_type}",
                f"标签：{'、'.join(material.tags)}",
                f"说话人：{'、'.join(material.speakers)}",
                f"入选原因：{material.value_reason}",
                f"片段原文：{material.transcript_text}",
            ]
        )

    def _build_filter(self, request: MaterialRecallRequest) -> str:
        filters: list[str] = []
        if request.video_id is not None:
            filters.append(f"video_id == {request.video_id}")
        if request.clip_type is not None:
            filters.append(f'clip_type == "{request.clip_type}"')
        if request.speaker is not None:
            filters.append(f'array_contains(speakers, "{request.speaker}")')
        if request.min_duration_ms is not None:
            filters.append(f"duration_ms >= {request.min_duration_ms}")
        if request.max_duration_ms is not None:
            filters.append(f"duration_ms <= {request.max_duration_ms}")
        return " and ".join(filters)

    def _to_recall_item(self, rank: int, hit: dict) -> dict:
        entity = hit.get("entity") or {}
        return {
            "rank": rank,
            "score": float(hit.get("distance") or hit.get("score") or 0),
            "material_id": int(entity.get("material_id") or 0),
            "video_id": int(entity.get("video_id") or 0),
            "clip_type": entity.get("clip_type") or "",
            "duration_ms": int(entity.get("duration_ms") or 0),
            "tags": list(entity.get("tags") or []),
            "speakers": list(entity.get("speakers") or []),
            "content": entity.get("text") or "",
        }

    def _validate_schema(self, client: MilvusClient, collection_name: str) -> None:
        description = client.describe_collection(collection_name=collection_name)
        field_names = {field["name"] for field in description.get("fields", [])}
        required_fields = {
            "id",
            "material_id",
            "video_id",
            "task_id",
            "clip_type",
            "duration_ms",
            "tags",
            "speakers",
            "text",
            "dense_vector",
            "sparse_vector",
        }
        missing_fields = sorted(required_fields - field_names)
        if missing_fields:
            raise RuntimeError(
                f"视频素材 Collection {collection_name} 缺少字段 {missing_fields}，请删除后重新创建"
            )
