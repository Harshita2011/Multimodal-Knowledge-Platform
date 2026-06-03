from collections import defaultdict

from app.models.domain.entities import RetrievedChunk


class RRFMerger:
    def __init__(self, k: int = 60, weights: dict[str, float] | None = None):
        self.k = k
        self.weights = weights or {"vector": 1.0, "bm25": 1.0, "entity": 1.0}

    def merge(self, channels: dict[str, list[RetrievedChunk]]) -> tuple[list[RetrievedChunk], dict[str, dict]]:
        scores: dict[str, float] = defaultdict(float)
        best_chunk: dict[str, RetrievedChunk] = {}
        trace: dict[str, dict] = defaultdict(dict)
        for channel, items in channels.items():
            w = self.weights.get(channel, 1.0)
            for rank, chunk in enumerate(items, start=1):
                score = w * (1.0 / (self.k + rank))
                scores[chunk.chunk_id] += score
                best_chunk[chunk.chunk_id] = chunk if chunk.chunk_id not in best_chunk else (
                    chunk if chunk.score > best_chunk[chunk.chunk_id].score else best_chunk[chunk.chunk_id]
                )
                trace[chunk.chunk_id][f"{channel}_score"] = chunk.score
                trace[chunk.chunk_id][f"{channel}_rank"] = rank
        ordered = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        out: list[RetrievedChunk] = []
        for cid, rrf_score in ordered:
            c = best_chunk[cid].model_copy(update={"score": min(1.0, best_chunk[cid].score + rrf_score)})
            out.append(c)
            trace[cid]["rrf_score"] = round(rrf_score, 6)
            present = [k.split("_")[0] for k in trace[cid].keys() if k.endswith("_score") and k != "rrf_score"]
            trace[cid]["retrieval_source"] = present[0] if len(present) == 1 else "multi"
        return out, trace
