from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import Device


class GeminiEmbeddingFunction:
    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name

    def name(self) -> str:
        return f"gemini:{self.model_name}"

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=texts,
        )
        return [item.values for item in response.embeddings]

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self._embed_texts(input)

    def embed_documents(self, texts=None, input=None) -> list[list[float]]:
        values = texts if texts is not None else input
        return self._embed_texts(list(values))

    def embed_query(self, text=None, input=None) -> list[float]:
        value = text if text is not None else input
        return [self._embed_texts([value])[0]]


@dataclass
class RetrievedContext:
    documents: list[str]
    metadatas: list[dict]


class DeviceRAGService:
    STATUS_ALIASES = {
        "active": {
            "active",
            "online",
            "running",
            "working",
            "available",
        },
        "offline": {
            "offline",
            "down",
            "disconnected",
            "not working",
            "unavailable",
        },
        "maintenance": {
            "maintenance",
            "maintaining",
            "repair",
            "servicing",
        },
    }

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        embedding_model: str | None = None,
        collection_name: str | None = None,
        persist_directory: str | None = None,
        chroma_client=None,
        gemini_client=None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.embedding_model = embedding_model or settings.GEMINI_EMBEDDING_MODEL
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
        self._chroma_client = chroma_client
        self._gemini_client = gemini_client
        self._collection = None

    def _validate_api_key(self) -> None:
        if not self.api_key:
            raise ImproperlyConfigured("GEMINI_API_KEY is not configured.")

        placeholder_fragments = (
            "replace-this",
            "your-api-key",
            "your_gemini_api_key",
        )
        if any(fragment in self.api_key.lower() for fragment in placeholder_fragments):
            raise ImproperlyConfigured(
                "GEMINI_API_KEY still looks like a placeholder value. "
                "Set it to a real Gemini API key before using RAG."
            )

    def _get_genai_client(self):
        if self._gemini_client is not None:
            return self._gemini_client

        self._validate_api_key()

        from google import genai

        self._gemini_client = genai.Client(api_key=self.api_key)
        return self._gemini_client

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        if self._chroma_client is None:
            import chromadb

            self._chroma_client = chromadb.PersistentClient(path=self.persist_directory)

        collection = self._chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=GeminiEmbeddingFunction(
                client=self._get_genai_client(),
                model_name=self.embedding_model,
            ),
            metadata={"hnsw:space": "cosine"},
        )
        self._collection = collection
        return collection

    @staticmethod
    def build_device_document(device: Device) -> str:
        session_lines = []
        sessions = list(device.sessions.all().order_by("-start_time")[:5])

        if sessions:
            for session in sessions:
                timestamp = session.start_time.isoformat()
                session_lines.append(
                    f"- Session at {timestamp} used {session.energy_consumed:.2f} kWh"
                )
        else:
            session_lines.append("- No sessions recorded yet")

        return "\n".join(
            [
                f"Device name: {device.name}",
                f"Serial number: {device.serial_number}",
                f"Status: {device.status}",
                f"Owner id: {device.owner_id}",
                f"Created at: {device.created_at.isoformat()}",
                "Recent sessions:",
                *session_lines,
            ]
        )

    @staticmethod
    def infer_status_filter(question: str) -> str | None:
        normalized = question.lower()
        for status, aliases in DeviceRAGService.STATUS_ALIASES.items():
            for alias in aliases:
                if alias in normalized:
                    return status
        return None

    def upsert_devices(self, devices: Iterable[Device]) -> int:
        device_list = list(devices)
        if not device_list:
            return 0

        collection = self._get_collection()
        collection.upsert(
            ids=[f"device-{device.pk}" for device in device_list],
            documents=[self.build_device_document(device) for device in device_list],
            metadatas=[
                {
                    "device_id": device.pk,
                    "owner_id": device.owner_id,
                    "status": device.status,
                    "serial_number": device.serial_number,
                }
                for device in device_list
            ],
        )
        return len(device_list)

    def retrieve(self, question: str, *, owner_id: int, limit: int = 3) -> RetrievedContext:
        collection = self._get_collection()
        where_clause = {"owner_id": owner_id}
        status_filter = self.infer_status_filter(question)
        if status_filter:
            where_clause = {
                "$and": [
                    {"owner_id": owner_id},
                    {"status": status_filter},
                ]
            }

        result = collection.query(
            query_texts=[question],
            n_results=limit,
            where=where_clause,
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return RetrievedContext(documents=documents, metadatas=metadatas)

    def answer(self, question: str, *, owner_id: int, limit: int = 3) -> dict:
        context = self.retrieve(question, owner_id=owner_id, limit=limit)
        if not context.documents:
            return {
                "answer": "I could not find any indexed device context for this user yet.",
                "matches": [],
            }

        status_filter = self.infer_status_filter(question)
        prompt_rules = [
            "You are answering questions about a user's IoT devices.",
            "Use only the retrieved context.",
            "If the context is insufficient, say so plainly.",
            "Do not invent devices, statuses, or serial numbers.",
        ]
        if status_filter:
            prompt_rules.extend(
                [
                    f"The user is asking specifically about devices with status '{status_filter}'.",
                    f"Only include devices whose status is exactly '{status_filter}'.",
                    "Ignore retrieved devices with any other status, even if they appear in the context.",
                    "If no retrieved device matches that exact status, say that no matching device was found in the retrieved context.",
                ]
            )

        prompt = "\n\n".join(
            [
                "\n".join(prompt_rules),
                f"Question: {question}",
                "Retrieved context:",
                "\n\n".join(context.documents),
            ]
        )

        response = self._get_genai_client().models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        answer_text = getattr(response, "text", None)
        if not answer_text:
            answer_text = "Gemini returned no text response for this question."

        return {
            "answer": answer_text,
            "matches": [
                {
                    "document": document,
                    "metadata": metadata,
                }
                for document, metadata in zip(context.documents, context.metadatas)
            ],
        }
