import os
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI

# ---------------------------------------------------------------------
# Inicialización robusta (compatible con sk- y sk-proj-)
# ---------------------------------------------------------------------
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "").strip()
ORG_ID = os.getenv("OPENAI_ORG_ID", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not API_KEY:
    raise ValueError("❌ No se encontró OPENAI_API_KEY en el entorno o está vacía.")

# Debug informativo
print(f"🧬 Tipo de clave: {'project' if API_KEY.startswith('sk-proj-') else 'personal'}")
print(f"📦 Project ID: {PROJECT_ID or '(no definido)'}")

# --- Creación del cliente ---
if API_KEY.startswith("sk-proj-"):
    # Workaround: definir cabeceras explícitas (SDK 1.44+ bug)
    headers = {"Authorization": f"Bearer {API_KEY}"}
    if PROJECT_ID:
        headers["OpenAI-Project"] = PROJECT_ID
    if ORG_ID:
        headers["OpenAI-Organization"] = ORG_ID
    client = OpenAI(api_key=API_KEY, default_headers=headers)
else:
    client = OpenAI(api_key=API_KEY)

# ---------------------------------------------------------------------
# Función para consultas
# ---------------------------------------------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def ask_model(prompt: str,
              temperature: float = 0.5,
              max_tokens: int = 2000,
              system: str = "Eres un analista de inteligencia estratégica. Sé preciso, verificable y claro.") -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error en ask_model: {e}")
        raise


