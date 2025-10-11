
# Global Intelligence Forecast — Proyecto Python

Pipeline OSINT + LLM que recopila noticias por país, analiza (economía, seguridad interior, diplomacia, dinámica social), genera previsiones y emite **informe bilingüe (ES/EN)** en Markdown.

## 🚀 Uso rápido

```bash
cd global_intel
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env  # edita con tus claves
python main.py
```

### Variables (.env)
- `OPENAI_API_KEY` — clave de OpenAI
- `OPENAI_MODEL` — recomendado: `gpt-4o-mini` o superior
- `NEWSAPI_KEY` — opcional, si quieres usar NewsAPI

### Configuración (`config.yaml`)
- `run.days_back`: días hacia atrás (default: 365)
- `run.per_country_limit`: artículos por país
- `run.providers`: `gdelt`, `newsapi`
- `countries`: lista inicial de países (puedes ampliarla a todos los ISO-3166)

## 🧠 Salida
Se genera un Markdown en `outputs/` con ambas versiones (**español** y **inglés**) y estructura limpia.

## ⚠️ Legal / Ética
Respeta términos de servicio de fuentes y APIs (scraping/uso justo). Este proyecto es para fines OSINT/Inteligencia respetando normativa vigente.
