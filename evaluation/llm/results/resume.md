# Résumé comparatif des modèles LLM (SA-33)

| Modèle | Note humaine (/2) | Mots-clés (%) | Fausses infos | Cohérence reform. (%) | Latence méd. (ms) | Latence p95 (ms) | Coût / 1000 req ($) | Erreurs (%) | Score global (/100) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-OSS 20B (Groq - Petit) (`openai/gpt-oss-20b`) | 1.73 | 75.0% | 0 | 66.7% | 1504.0 | 5751.8 | $0.1142 | 24.2% | **81.1** |
| GPT-OSS 120B (Groq - Grand) (`openai/gpt-oss-120b`) | 1.86 | 72.1% | 0 | 100.0% | 1216.0 | 6009.8 | $0.2303 | 23.3% | **76.3** |
| Mistral 7B (Ollama Local) (`mistral`) | 1.73 | 90.8% | 0 | 100.0% | 17203.3 | 103634.7 | $0.0000 | 6.7% | **75.9** |
