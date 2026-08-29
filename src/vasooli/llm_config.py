import os

# Configuration for Groq LLM Classifier
# Default model: qwen/qwen3.8-27b
LLM_MODEL = os.environ.get("GROQ_LLM_MODEL", "qwen/qwen3.8-27b")
