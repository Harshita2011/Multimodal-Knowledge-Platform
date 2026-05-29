from collections import defaultdict

from app.models.domain.entities import RetrievedChunk


class ChunkDiversifier:
    def __init__(self, diversity_lambda: float = 0.2):
        self.diversity_lambda = diversity_lambda

    def diversify(self, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        if not chunks or top_k <= 0:
            return []
        selected: list[RetrievedChunk] = []
        page_counts: dict[int, int] = defaultdict(int)
        pool = chunks[:]

        while pool and len(selected) < top_k:
            best_idx = 0
            best_score = float("-inf")
            for i, chunk in enumerate(pool):
                penalty = self.diversity_lambda * page_counts[chunk.metadata.page_number]
                score = chunk.score - penalty
                if score > best_score:
                    best_score = score
                    best_idx = i
                elif score == best_score and chunk.chunk_id < pool[best_idx].chunk_id:
                    best_idx = i
            pick = pool.pop(best_idx)
            selected.append(pick)
            page_counts[pick.metadata.page_number] += 1
        return selected
