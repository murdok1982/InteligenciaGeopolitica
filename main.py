import os, json, math
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
from tqdm import tqdm
from jinja2 import Template

# ================================
# 🚀 Carga forzada de entorno
# ================================
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    env_data = dotenv_values(env_path)
    os.environ.update(env_data)
load_dotenv(dotenv_path=env_path, override=True)

print("🔑 Clave detectada (inicio main.py):", os.getenv("OPENAI_API_KEY", "NO ENCONTRADA")[:12], "...")

# ================================
# 🔧 Importación de módulos locales
# (después de cargar .env)
# ================================
from utils.io import load_config, ensure_dir, ts_stamp, save_text
from utils.regions import region_for
from utils.llm import ask_model
from providers.gdelt_provider import search_gdelt
from providers.newsapi_provider import search_newsapi



# --- carga forzada del .env ---
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    env_data = dotenv_values(env_path)
    os.environ.update(env_data)
load_dotenv(dotenv_path=env_path, override=True)

print("🔑 Clave detectada (inicio main.py):", os.getenv("OPENAI_API_KEY", "NO ENCONTRADA")[:12], "...")


CATEGORIES = [
    ("economía", "economy"),
    ("seguridad interior", "internal_security"),
    ("relaciones diplomáticas", "diplomacy"),
    ("dinámica social", "social_dynamics"),
]

def read_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def render_template(tpl_str: str, **kwargs):
    return Template(tpl_str).render(**kwargs)

def collect_articles(country_name, days_back, per_country_limit, use_gdelt=True, use_newsapi=True):
    pool = []
    per_cat = max(2, math.ceil(per_country_limit / len(CATEGORIES)))
    for cat_es, cat_en in CATEGORIES:
        if use_gdelt:
            pool += search_gdelt(country_name, cat_es, days_back=days_back, limit=per_cat)
        if use_newsapi:
            pool += search_newsapi(country_name, cat_es, days_back=days_back, limit=per_cat, language="en")
    # de-duplicate by URL
    seen = set()
    deduped = []
    for a in pool:
        url = a.get("url","")
        if url and url not in seen:
            seen.add(url)
            deduped.append(a)
    return deduped[:per_country_limit]

def build_country_section_es(name, region, analysis, forecast):
    return (
        f"\n## País: {name}\n"
        f"**Región:** {region}\n\n"
        f"### Análisis (últimos 12 meses)\n{analysis}\n\n"
        f"### Previsión (6m / 1a / 3a)\n{forecast}\n"
    )

def main():
    load_dotenv()
    from pathlib import Path
    from dotenv import dotenv_values

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
     env_data = dotenv_values(env_path)
     os.environ.update(env_data)

    print("🔑 Clave detectada:", os.getenv("OPENAI_API_KEY", "NO CARGADA")[:10], "...")
    # ✅ Validación temprana de claves y configuración
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key or not openai_key.startswith("sk-"):
        print("⚠️  ERROR: No se ha configurado una clave válida de OpenAI.")
        print("👉 Edita tu archivo .env y añade una línea como:")
        print("   OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        print("Luego vuelve a ejecutar: python main.py\n")
        return

    print("✅ Clave OpenAI detectada correctamente.")

    cfg = load_config("config.yaml")
    days_back = cfg["run"]["days_back"]
    per_country_limit = cfg["run"]["per_country_limit"]
    providers = cfg["run"]["providers"]
    output_dir = cfg["report"]["output_dir"]
    ensure_dir(output_dir)

    use_gdelt = "gdelt" in providers
    use_newsapi = "newsapi" in providers

    analysis_prompt_tpl = read_prompt("prompts/analysis_es.txt")
    forecast_prompt_tpl = read_prompt("prompts/forecast_es.txt")
    synthesis_prompt_tpl = read_prompt("prompts/synthesis_es.txt")
    report_tpl = read_prompt("prompts/report_bilingual.txt")

    country_sections_es, country_sections_en = [], []
    region_blobs_es = {}

    print("🔎 Recolectando y analizando países...")
    for c in tqdm(cfg["countries"]):
        name, code = c["name"], c["code"]
        region = region_for(code)

        articles = collect_articles(name, days_back, per_country_limit, use_gdelt, use_newsapi)
        bullets = "\n".join([f"- {a['title']} ({a.get('source','')}) {a['url']}" for a in articles])

        analysis_prompt = render_template(analysis_prompt_tpl, country=name, region=region) + f"\n\nContexto (titulares recientes):\n{bullets}"
        analysis_text = ask_model(analysis_prompt, temperature=0.5)

        forecast_prompt = render_template(forecast_prompt_tpl, country=name)
        forecast_text = ask_model(forecast_prompt + f"\n\nConsidera este contexto:\n{analysis_text}", temperature=0.6)

        section_es = build_country_section_es(name, region, analysis_text, forecast_text)
        section_en = ask_model("Translate the following Spanish country analysis+forecast into clear professional English Markdown:\n\n" + section_es, temperature=0.3)

        country_sections_es.append(section_es)
        country_sections_en.append(section_en)

        region_blobs_es.setdefault(region, []).append(section_es)

    # Síntesis regional (ES)
    regional_synthesis_es_parts = []
    for region, blobs in region_blobs_es.items():
        joined = "\n\n".join(blobs[:10])
        syn_es = ask_model(synthesis_prompt_tpl + f"\n\nContexto de {region} (extractos país):\n{joined}", temperature=0.5)
        regional_synthesis_es_parts.append(f"### {region}\n{syn_es}")
    regional_synthesis_es_text = "\n\n".join(regional_synthesis_es_parts)

    # Síntesis regional (EN)
    regional_synthesis_en_text = ask_model("Translate to English and tighten:\n\n" + regional_synthesis_es_text, temperature=0.3)

    # Panorama global (ES/EN)
    global_overview_es = ask_model("Elabora un panorama estratégico global (ES) a partir de estas síntesis regionales:\n\n" + regional_synthesis_es_text, temperature=0.5)
    global_overview_en = ask_model("Write a concise global strategic overview (EN) based on these regional syntheses:\n\n" + regional_synthesis_en_text, temperature=0.5)

    # Resúmenes ejecutivos
    executive_summary_es = ask_model("Resume en 10-14 líneas el panorama global ES, con viñetas de riesgos y oportunidades:\n\n" + global_overview_es, temperature=0.4)
    executive_summary_en = ask_model("Summarize in 10-14 lines the global outlook EN, include bullets for risks and opportunities:\n\n" + global_overview_en, temperature=0.4)

    # Render reporte final
    report_md = Template(report_tpl).render(
        executive_summary_es=executive_summary_es,
        regional_synthesis_es=regional_synthesis_es_text,
        country_sections_es="\n\n".join(country_sections_es),
        global_overview_es=global_overview_es,
        executive_summary_en=executive_summary_en,
        regional_synthesis_en=regional_synthesis_en_text,
        country_sections_en="\n\n".join(country_sections_en),
        global_overview_en=global_overview_en
    )

    out_dir = cfg["report"]["output_dir"]
    from utils.io import save_text, ts_stamp
    fname = f"{cfg['report']['filename_prefix']}_{ts_stamp()}.md"
    save_text(os.path.join(out_dir, fname), report_md)
    print(f"✅ Reporte generado: {os.path.join(out_dir, fname)}")

if __name__ == "__main__":
    main()
