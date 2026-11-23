import anthropic
import json, os, requests
import chromadb

client = anthropic.Anthropic()
MODEL = "claude-haiku-5-5"
TOPE_TOKENS = 15_000          # tope duro para toda la sesión

class Presupuesto:
    def __init__(self, maximo):
        self.maximo, self.usado = maximo, 0
    def verificar(self):
        if self.usado >= self.maximo:
            raise RuntimeError(f"Presupuesto agotado: {self.usado} tokens")
    def sumar(self, usage):
        self.usado += usage.input_tokens + usage.output_tokens

presupuesto = Presupuesto(TOPE_TOKENS)

TEMAS = ["Retrieval-augmented generation", "Large language model",
         "Regulation of artificial intelligence", "AI alignment",
         "Prompt engineering"]

def traer(titulo):
    r = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "prop": "extracts", "explaintext": 1,
                "titles": titulo, "format": "json", "redirects": 1},
        headers={"User-Agent": "rag-demo/0.1 (aprendizaje)"}, timeout=20)
    pagina = next(iter(r.json()["query"]["pages"].values()))
    return pagina.get("extract", "")[:12000]   # solo el comienzo

def cargar_corpus():
    if not os.path.exists("corpus.json"):
        corpus = {t: traer(t) for t in TEMAS}
        json.dump(corpus, open("corpus.json", "w"))
    return json.load(open("corpus.json"))

def trocear(texto, tam=200, solape=30):
    palabras = texto.split()
    for i in range(0, len(palabras), tam - solape):
        yield " ".join(palabras[i:i + tam])

def armar_db(corpus):
    db = chromadb.PersistentClient(path="chroma_db").get_or_create_collection("wiki")
    if db.count() == 0:
        docs, metas, ids = [], [], []
        for titulo, texto in corpus.items():
            for n, frag in enumerate(trocear(texto)):
                docs.append(frag)
                metas.append({"fuente": titulo})
                ids.append(f"{titulo}-{n}")
        db.add(documents=docs, metadatas=metas, ids=ids)
    return db

def buscar(db, consulta, k=2):
    r = db.query(query_texts=[consulta], n_results=k)
    return "\n".join(f"[{m['fuente']}] {d}"
                     for d, m in zip(r["documents"][0], r["metadatas"][0]))

def agente(rol, mensaje, max_salida):
    presupuesto.verificar()
    r = client.messages.create(
        model=MODEL, max_tokens=max_salida,
        system=rol, messages=[{"role": "user", "content": mensaje}])
    presupuesto.sumar(r.usage)
    if r.stop_reason == "max_tokens":
        print("   ⚠️ Respuesta cortada por el límite de tokens")
    print(f"   ({r.usage.input_tokens} in / {r.usage.output_tokens} out)")
    return "".join(b.text for b in r.content if b.type == "text")

INVESTIGADOR = """Convertí la pregunta en 2 consultas de búsqueda cortas
en inglés, una por línea. Sin explicaciones."""

REDACTOR = """Respondé en español, en máximo 3 oraciones, usando SOLO las
fuentes dadas. Si no alcanzan, decí 'No tengo información suficiente'.
Indicá la fuente entre corchetes."""

REVISOR = """Compará la respuesta con las fuentes. Si todo está respaldado
respondé exactamente APROBADO. Si hay algo sin respaldo, respondé RECHAZADO
y una frase de qué corregir."""

def responder(db, pregunta):
    consultas = agente(INVESTIGADOR, pregunta, 200).splitlines()[:2]
    fuentes = "\n".join(buscar(db, c) for c in consultas if c.strip())
    base = f"Pregunta: {pregunta}\n\nFuentes:\n{fuentes}"

    respuesta = agente(REDACTOR, base, 800)
    veredicto = agente(REVISOR, f"{base}\n\nRespuesta:\n{respuesta}", 400)

    if not veredicto.startswith("APROBADO"):      # máximo 1 corrección
        respuesta = agente(
            REDACTOR, f"{base}\n\nCorregí según: {veredicto}", 800)
    return respuesta, veredicto

if __name__ == "__main__":
    corpus = cargar_corpus()
    db = armar_db(corpus)

    preguntas = [
        "¿Qué es RAG y para qué sirve?",
        "¿Quién ganó el Mundial de fútbol de 2022?",   # no está en el corpus
    ]
    for p in preguntas:
        print(f"\n❓ {p}")
        respuesta, veredicto = responder(db, p)
        print("💬", respuesta)
        print("🔎 Revisor:", veredicto[:120])
        print(f"📊 Tokens usados: {presupuesto.usado}/{TOPE_TOKENS}")