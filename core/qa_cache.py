"""
core/qa_cache.py

A semantic Q&A cache: before generating a real reply, check whether a
sufficiently similar question has already been answered, using
core.llm.embed() to compare meaning rather than exact wording. 

"""

import json
import math
import re

from django.core.cache import cache
from redis.exceptions import RedisError

from core.llm import LLMError, embed

QA_CACHE_KEY = "qa_cache:entries"
SIMILARITY_THRESHOLD = 0.81  # cosine similarity; a starting guess, tune once there's real traffic to check it against
MAX_ENTRIES = 300  # oldest entries drop off past this, so the cache can't grow unbounded

def _numbers_in(text):
    """Every distinct number mentioned in the text, as strings (e.g. mukhi counts)."""
    return set(re.findall(r"\d+", text))

def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_entries():
    raw = cache.get(QA_CACHE_KEY)
    return json.loads(raw) if raw else []


def _save_entries(entries):
    cache.set(QA_CACHE_KEY, json.dumps(entries), timeout=None)


def get_cached_reply(question):
    """
    Returns the cached reply for the closest sufficiently-similar past
    question, or None on a miss (nothing clears the similarity threshold,
    the cache is empty, or embedding the question failed).
    """
    try:
        query_vector = embed(question)
    except LLMError:
        return None
 
    try:
        entries = _load_entries()
    except RedisError:
        return None
 
    query_numbers = _numbers_in(question)
    
    best_score = 0.0
    best_reply = None
    for entry in entries:
        if _numbers_in(entry["question"]) != query_numbers:
            continue  
        score = _cosine_similarity(query_vector, entry["embedding"])
        if score > best_score:
            best_score = score
            best_reply = entry["reply"]
 
    return best_reply if best_score >= SIMILARITY_THRESHOLD else None


def store_reply(question, reply):
    """Caches a reply against this question's embedding."""
    try:
        vector = embed(question)
    except LLMError:
        return
 
    try:
        entries = _load_entries()
        entries.append({
            "question": question,
            "embedding": [round(x, 6) for x in vector],  # trims storage size, negligible accuracy loss
            "reply": reply,
        })
        _save_entries(entries[-MAX_ENTRIES:])
    except RedisError:
        return

def clear_all():
    """Wipes every cached Q&A pair - called by sync_products on completion."""
    try:
        cache.delete(QA_CACHE_KEY)
    except RedisError:
        pass