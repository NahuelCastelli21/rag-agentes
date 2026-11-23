# RAG con 3 agentes

Sistema simple de preguntas y respuestas sobre documentos de Wikipedia.

- **Investigador:** convierte la pregunta en consultas de búsqueda.
- **Redactor:** responde solo con las fuentes recuperadas, citándolas.
- **Revisor:** verifica que la respuesta esté respaldada; si no, pide corregirla.

## Controles incluidos
- Tope de tokens por sesión y `max_tokens` por agente.
- Aviso cuando una respuesta se corta por límite.
- Máximo 1 corrección por pregunta.
- Si las fuentes no alcanzan, el sistema lo dice en vez de inventar.

## Cómo correrlo
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY="tu_clave"   # en Windows: $env:ANTHROPIC_API_KEY="tu_clave"
python rag_agentes.py
```