import streamlit as st
import os
import json
import requests
from groq import Groq

st.set_page_config(page_title="Fiche Pro — Audit & Génération", layout="wide", page_icon="📦")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

# ── CSS THÈME CLAIR ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f8f9fb; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5e7eb; }
  .main-header {
    background: #ffffff;
    border-bottom: 2px solid #e5e7eb;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    border-radius: 10px;
  }
  .metric-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .score-big {
    font-size: 3rem;
    font-weight: 900;
    text-align: center;
    margin: 0.5rem 0;
  }
  .score-green { color: #059669; }
  .score-orange { color: #d97706; }
  .score-red { color: #dc2626; }
  .reco-item {
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    margin-bottom: 0.3rem;
    font-size: 0.85rem;
  }
  .reco-ok { background: #f0fdf4; border-left: 3px solid #059669; color: #065f46; }
  .reco-ko { background: #fef2f2; border-left: 3px solid #dc2626; color: #991b1b; }
  .reco-warn { background: #fffbeb; border-left: 3px solid #d97706; color: #92400e; }
  .asin-box {
    background: #ffffff;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }
  .product-preview {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  div[data-testid="stButton"] button {
    background: #059669 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
  }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
st.sidebar.image("https://via.placeholder.com/150x40/059669/ffffff?text=Fiche+Pro", width=150)
st.sidebar.markdown("---")
mode = st.sidebar.radio("Mode", ["🔍 Audit de fiche", "✍️ Générer une fiche"])
st.sidebar.markdown("---")
st.sidebar.markdown("🔗 [Ads Optimizer Pro](https://amazon-optimizer-rwjs.onrender.com)")
st.sidebar.markdown("*by AilteqFrance*")

# ── FONCTIONS SCRAPING ─────────────────────────────────────────────────────────
def extract_asin(input_text):
    """Extrait l'ASIN depuis une URL ou texte brut."""
    import re
    input_text = input_text.strip()
    # Format ASIN direct
    if re.match(r'^[A-Z0-9]{10}$', input_text):
        return input_text
    # URL Amazon
    match = re.search(r'/dp/([A-Z0-9]{10})', input_text)
    if match:
        return match.group(1)
    match = re.search(r'/gp/product/([A-Z0-9]{10})', input_text)
    if match:
        return match.group(1)
    return None

def scrape_amazon(asin, marketplace="fr"):
    """Scrape la fiche Amazon via ScraperAPI."""
    if not SCRAPER_API_KEY:
        return None, "Clé ScraperAPI manquante"
    
    url = f"https://www.amazon.{marketplace}/dp/{asin}"
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "autoparse": "true",
        "country_code": marketplace,
    }
    
    try:
        resp = requests.get("https://api.scraperapi.com/", params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data, None
        return None, f"Erreur HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

def parse_product_data(data):
    """Parse les données ScraperAPI en format utilisable."""
    if not data:
        return {}
    
    product = {}
    
    # ScraperAPI autoparse format
    product["titre"] = data.get("name", data.get("title", ""))
    product["prix"] = data.get("pricing", data.get("price", ""))
    product["note"] = data.get("stars", data.get("rating", 0))
    product["nb_avis"] = data.get("total_reviews", data.get("reviews_count", 0))
    
    # Bullets
    features = data.get("feature_bullets", data.get("features", []))
    if isinstance(features, list):
        for i, f in enumerate(features[:5], 1):
            product[f"bullet{i}"] = f if isinstance(f, str) else str(f)
    
    # Description
    product["description"] = data.get("description", data.get("product_description", ""))
    
    # Images
    images = data.get("images", data.get("image_list", []))
    product["nb_images"] = len(images) if isinstance(images, list) else 0
    
    # A+
    product["a_plus"] = bool(data.get("aplus_content", data.get("enhanced_content", False)))
    
    return product

# ── FONCTIONS IA ───────────────────────────────────────────────────────────────
def appel_groq(prompt, json_mode=True):
    try:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            **kwargs
        )
        content = resp.choices[0].message.content
        if json_mode:
            return json.loads(content)
        return content
    except Exception as e:
        st.error(f"Erreur Groq : {e}")
        return None

def score_color_class(score, max_score):
    pct = score / max_score * 100
    if pct >= 75: return "score-green"
    if pct >= 50: return "score-orange"
    return "score-red"

def afficher_reco(items):
    for item in items:
        icon = item.get("icon", "✅")
        texte = item.get("texte", "")
        type_ = item.get("type", "ok")
        cls = "reco-ok" if type_ == "ok" else ("reco-ko" if type_ == "ko" else "reco-warn")
        st.markdown(f'<div class="reco-item {cls}">{icon} {texte}</div>', unsafe_allow_html=True)

def lancer_audit(titre, bullet1, bullet2, bullet3, bullet4, bullet5,
                  description, mot_cle_principal, categorie, prix,
                  nb_avis, note, nb_images, a_plus):
    bullets = "\n".join([b for b in [bullet1, bullet2, bullet3, bullet4, bullet5] if b and b.strip()])
    
    prompt = f"""Tu es un expert Amazon FBA spécialisé dans l'optimisation de fiches produit pour Amazon France.

Analyse cette fiche produit Amazon et retourne un JSON avec le format EXACT suivant :

{{
  "score_global": <nombre entre 0 et 100>,
  "sections": {{
    "titre": {{
      "score": <0 à 25>,
      "max": 25,
      "items": [
        {{"icon": "✅", "type": "ok", "texte": "..."}},
        {{"icon": "❌", "type": "ko", "texte": "..."}}
      ]
    }},
    "images": {{
      "score": <0 à 20>,
      "max": 20,
      "items": [...]
    }},
    "bullets": {{
      "score": <0 à 20>,
      "max": 20,
      "items": [...]
    }},
    "seo": {{
      "score": <0 à 20>,
      "max": 20,
      "items": [...]
    }},
    "preuve_sociale": {{
      "score": <0 à 15>,
      "max": 15,
      "items": [...]
    }}
  }},
  "top3_actions": ["action 1", "action 2", "action 3"],
  "titre_optimise": "<propose un titre optimisé>",
  "bullet_optimise": "<propose un bullet point amélioré basé sur le bullet 1>"
}}

Données de la fiche :
- Titre : {titre}
- Mot-clé principal cible : {mot_cle_principal or 'non spécifié'}
- Catégorie : {categorie or 'non spécifiée'}
- Bullets : {bullets or 'non renseignés'}
- Description : {description or 'non renseignée'}
- Prix : {prix}€
- Avis : {nb_avis} avis, note {note}/5
- Images : {nb_images} images
- A+ Content : {'Oui' if a_plus else 'Non'}

Sois précis, critique et actionnable. Réponds UNIQUEMENT en JSON valide."""

    with st.spinner("Analyse IA en cours..."):
        return appel_groq(prompt)

def afficher_resultats(result):
    if not result:
        return
    
    score = result.get("score_global", 0)
    sections = result.get("sections", {})

    st.markdown("---")
    st.markdown("## 📊 Résultats de l'audit")

    col_score, col_top3 = st.columns([1, 2])
    with col_score:
        cls = "score-green" if score >= 75 else ("score-orange" if score >= 50 else "score-red")
        label = "EXCELLENT" if score >= 75 else ("À AMÉLIORER" if score >= 50 else "CRITIQUE")
        st.markdown(f"""
        <div class="metric-card" style="text-align:center">
            <div style="font-size:0.75rem;letter-spacing:2px;color:#6b7280">SCORE GLOBAL</div>
            <div class="score-big {cls}">{score}/100</div>
            <div style="font-size:0.85rem;color:#6b7280;font-weight:600">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_top3:
        st.markdown("### 🎯 Top 3 actions prioritaires")
        for i, action in enumerate(result.get("top3_actions", []), 1):
            st.markdown(f"**{i}.** {action}")

    st.markdown("---")
    section_labels = {
        "titre": "📝 Titre",
        "images": "🖼️ Images",
        "bullets": "🎯 Bullet Points",
        "seo": "🔍 SEO",
        "preuve_sociale": "⭐ Preuve Sociale"
    }

    cols = st.columns(2)
    for i, (key, label) in enumerate(section_labels.items()):
        sec = sections.get(key, {})
        sc = sec.get("score", 0)
        mx = sec.get("max", 20)
        items = sec.get("items", [])
        cls = score_color_class(sc, mx)

        with cols[i % 2]:
            st.markdown(f"""
            <div class="metric-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                <span style="font-weight:700;color:#111827">{label}</span>
                <span class="{cls}" style="font-size:1.1rem;font-weight:800">{sc}/{mx}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            afficher_reco(items)
            st.markdown("")

    st.markdown("---")
    st.markdown("### 💡 Suggestions IA")
    col_t, col_b = st.columns(2)
    with col_t:
        st.markdown("**Titre optimisé suggéré :**")
        st.info(result.get("titre_optimise", "—"))
    with col_b:
        st.markdown("**Bullet point amélioré :**")
        st.info(result.get("bullet_optimise", "—"))

# ── MODE AUDIT ─────────────────────────────────────────────────────────────────
if mode == "🔍 Audit de fiche":
    st.title("🔍 Audit de Fiche Produit Amazon")
    st.markdown("Entrez un ASIN ou collez les informations manuellement.")
    st.markdown("---")

    # ASIN auto
    st.markdown("### 🤖 Récupération automatique")
    col_asin, col_mkt = st.columns([3, 1])
    with col_asin:
        asin_input = st.text_input("ASIN ou URL Amazon", placeholder="Ex: B073JYC4XM ou https://www.amazon.fr/dp/B073JYC4XM")
    with col_mkt:
        marketplace = st.selectbox("Marketplace", ["fr", "com", "co.uk", "de", "es", "it"])

    mot_cle_principal = st.text_input("🔑 Mot-clé principal cible", placeholder="Ex: thermomètre frontal sans contact")

    # Données produit (remplies auto ou manuellement)
    if "product_data" not in st.session_state:
        st.session_state.product_data = {}

    col_fetch, col_manual = st.columns(2)
    with col_fetch:
        if st.button("🔄 Récupérer les données Amazon", use_container_width=True):
            asin = extract_asin(asin_input)
            if not asin:
                st.error("ASIN invalide — vérifiez le format (ex: B073JYC4XM)")
            else:
                with st.spinner(f"Récupération de la fiche {asin} sur Amazon.{marketplace}..."):
                    data, err = scrape_amazon(asin, marketplace)
                if err:
                    st.error(f"Erreur scraping : {err}")
                elif data:
                    parsed = parse_product_data(data)
                    st.session_state.product_data = parsed
                    st.success(f"✅ Fiche récupérée ! ASIN : {asin}")

    with col_manual:
        st.markdown("*Ou remplissez manuellement ci-dessous*")

    st.markdown("---")
    st.markdown("### 📋 Données de la fiche")

    pd = st.session_state.product_data
    col1, col2 = st.columns(2)
    with col1:
        titre = st.text_area("📝 Titre", value=pd.get("titre", ""), height=80)
        bullet1 = st.text_area("🎯 Bullet 1", value=pd.get("bullet1", ""), height=60)
        bullet2 = st.text_area("🎯 Bullet 2", value=pd.get("bullet2", ""), height=60)
        bullet3 = st.text_area("🎯 Bullet 3", value=pd.get("bullet3", ""), height=60)
        bullet4 = st.text_area("🎯 Bullet 4", value=pd.get("bullet4", ""), height=60)
        bullet5 = st.text_area("🎯 Bullet 5", value=pd.get("bullet5", ""), height=60)

    with col2:
        description = st.text_area("📄 Description", value=pd.get("description", ""), height=150)
        categorie = st.text_input("📂 Catégorie", placeholder="Ex: Santé & Soins du corps")
        try:
            prix_val = float(str(pd.get("prix", "25")).replace("€", "").replace(",", ".").strip().split()[0])
        except:
            prix_val = 25.0
        prix = st.number_input("💰 Prix (€)", value=prix_val, min_value=0.0, step=0.5)
        nb_avis = st.number_input("💬 Nombre d'avis", value=int(pd.get("nb_avis", 0)), min_value=0)
        note = st.slider("⭐ Note", 1.0, 5.0, float(pd.get("note", 4.0)), 0.1)
        nb_images = st.number_input("🖼️ Nombre d'images", value=int(pd.get("nb_images", 5)), min_value=0, max_value=9)
        a_plus = st.checkbox("✅ A+ Content présent", value=bool(pd.get("a_plus", False)))

    st.markdown("---")
    if st.button("🚀 Lancer l'audit", use_container_width=True, type="primary"):
        if not titre:
            st.warning("Veuillez renseigner le titre.")
        else:
            result = lancer_audit(titre, bullet1, bullet2, bullet3, bullet4, bullet5,
                                   description, mot_cle_principal, categorie, prix,
                                   nb_avis, note, nb_images, a_plus)
            afficher_resultats(result)

# ── MODE GÉNÉRATION ────────────────────────────────────────────────────────────
elif mode == "✍️ Générer une fiche":
    st.title("✍️ Générateur de Fiche Produit Amazon")
    st.markdown("Renseignez les informations de base — l'IA génère une fiche optimisée SEO.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        produit = st.text_input("📦 Nom du produit", placeholder="Ex: Thermomètre frontal infrarouge")
        mots_cles = st.text_area("🔑 Mots-clés cibles (un par ligne)", height=120,
                                  placeholder="thermomètre frontal\nthermomètre sans contact\nthermomètre bébé")
        categorie_gen = st.text_input("📂 Catégorie", placeholder="Ex: Santé & Soins du corps")
        prix_gen = st.number_input("💰 Prix (€)", min_value=0.0, value=25.0, step=0.5)

    with col2:
        avantages = st.text_area("✅ Avantages / caractéristiques clés", height=120,
                                  placeholder="Mesure en 1 seconde\nCertifié CE MDR\nAffichage LCD\nMémoire 30 mesures")
        public_cible = st.text_input("👥 Public cible", placeholder="Ex: Parents avec bébé, seniors")
        langue = st.selectbox("🌍 Langue", ["Français", "Anglais"])
        ton = st.selectbox("🎭 Ton", ["Professionnel", "Rassurant", "Dynamique"])

    st.markdown("---")

    if st.button("✨ Générer la fiche", use_container_width=True, type="primary"):
        if not produit:
            st.warning("Veuillez renseigner le nom du produit.")
        else:
            prompt_gen = f"""Tu es un expert copywriter Amazon spécialisé dans les fiches produit optimisées SEO pour Amazon France.

Génère une fiche produit Amazon complète et optimisée en {langue} avec un ton {ton}.

Retourne UNIQUEMENT un JSON valide avec ce format exact :
{{
  "titre": "<titre optimisé max 200 caractères avec mots-clés principaux>",
  "bullet1": "<bullet point 1 — commencer par un bénéfice en MAJUSCULES>",
  "bullet2": "<bullet point 2>",
  "bullet3": "<bullet point 3>",
  "bullet4": "<bullet point 4>",
  "bullet5": "<bullet point 5>",
  "description": "<description HTML Amazon 2000 caractères max>",
  "mots_cles_backend": "<mots-clés backend séparés par des espaces, max 250 octets>"
}}

Informations produit :
- Produit : {produit}
- Catégorie : {categorie_gen or 'non spécifiée'}
- Prix : {prix_gen}€
- Mots-clés cibles : {mots_cles or 'non spécifiés'}
- Avantages : {avantages or 'non spécifiés'}
- Public cible : {public_cible or 'non spécifié'}

Règles :
- Titre avec les 2-3 premiers mots-clés naturellement intégrés
- Chaque bullet commence par un bénéfice en MAJUSCULES suivi de " — " puis l'explication
- Description persuasive et rassurante
- Optimisé pour Amazon.fr"""

            with st.spinner("Génération en cours..."):
                result_gen = appel_groq(prompt_gen)

            if result_gen:
                st.markdown("---")
                st.success("✅ Fiche générée avec succès !")

                st.markdown("### 📝 Titre")
                titre_gen = result_gen.get("titre", "")
                st.info(titre_gen)
                st.caption(f"{len(titre_gen)} caractères")

                st.markdown("### 🎯 Bullet Points")
                for i in range(1, 6):
                    bp = result_gen.get(f"bullet{i}", "")
                    if bp:
                        st.markdown(f"**Bullet {i} :** {bp}")
                        st.caption(f"{len(bp)} caractères")

                st.markdown("### 📄 Description")
                st.text_area("Description", value=result_gen.get("description", ""), height=200)

                st.markdown("### 🔑 Mots-clés backend")
                st.text_area("Mots-clés backend", value=result_gen.get("mots_cles_backend", ""), height=80)

                export = f"""FICHE PRODUIT — {produit}
{'='*50}

TITRE:
{result_gen.get('titre', '')}

BULLET POINTS:
1. {result_gen.get('bullet1', '')}
2. {result_gen.get('bullet2', '')}
3. {result_gen.get('bullet3', '')}
4. {result_gen.get('bullet4', '')}
5. {result_gen.get('bullet5', '')}

DESCRIPTION:
{result_gen.get('description', '')}

MOTS-CLÉS BACKEND:
{result_gen.get('mots_cles_backend', '')}
"""
                st.download_button("⬇️ Télécharger la fiche (.txt)",
                                   export, f"fiche_{produit[:20].replace(' ','_')}.txt",
                                   use_container_width=True)
