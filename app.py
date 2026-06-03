import streamlit as st
import os
import json
from groq import Groq

st.set_page_config(page_title="Fiche Pro — Audit & Génération", layout="wide", page_icon="📦")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0f1318; }
  [data-testid="stSidebar"] { background: #111827; border-right: 1px solid #1e2d45; }
  h1, h2, h3 { font-family: 'Segoe UI', sans-serif !important; }
  .metric-card {
    background: #1a2235;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
  }
  .score-big {
    font-size: 3rem;
    font-weight: 900;
    text-align: center;
    margin: 0.5rem 0;
  }
  .score-green { color: #00d4a0; }
  .score-orange { color: #ff6b35; }
  .score-red { color: #ff4757; }
  .section-score {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.8rem;
    background: #111827;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    border-left: 3px solid #1e2d45;
  }
  .reco-item {
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    margin-bottom: 0.3rem;
    font-size: 0.85rem;
  }
  .reco-ok { background: rgba(0,212,160,0.1); border-left: 3px solid #00d4a0; }
  .reco-ko { background: rgba(255,71,87,0.1); border-left: 3px solid #ff4757; }
  .reco-warn { background: rgba(255,107,53,0.1); border-left: 3px solid #ff6b35; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
st.sidebar.title("📦 Fiche Pro")
st.sidebar.markdown("---")
mode = st.sidebar.radio("Mode", ["🔍 Audit de fiche", "✍️ Générer une fiche"])
st.sidebar.markdown("---")
st.sidebar.markdown("🔗 [Ads Optimizer Pro](https://amazon-optimizer-rwjs.onrender.com)")
st.sidebar.markdown("*by AilteqFrance*")

# ── FONCTIONS ──────────────────────────────────────────────────────────────────
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

def score_color(score, max_score):
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

# ── MODE AUDIT ─────────────────────────────────────────────────────────────────
if mode == "🔍 Audit de fiche":
    st.title("🔍 Audit de Fiche Produit Amazon")
    st.markdown("Collez les informations de votre fiche pour obtenir un score détaillé et des recommandations.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        titre = st.text_area("📝 Titre du produit", height=80, placeholder="Ex: Thermomètre Frontal Sans Contact...")
        bullet1 = st.text_area("🎯 Bullet point 1", height=60, placeholder="Premier avantage produit...")
        bullet2 = st.text_area("🎯 Bullet point 2", height=60, placeholder="Deuxième avantage...")
        bullet3 = st.text_area("🎯 Bullet point 3", height=60, placeholder="Troisième avantage...")
        bullet4 = st.text_area("🎯 Bullet point 4", height=60, placeholder="Quatrième avantage...")
        bullet5 = st.text_area("🎯 Bullet point 5", height=60, placeholder="Cinquième avantage...")

    with col2:
        description = st.text_area("📄 Description / A+ Content", height=150, placeholder="Description complète du produit...")
        mot_cle_principal = st.text_input("🔑 Mot-clé principal cible", placeholder="Ex: thermomètre frontal sans contact")
        categorie = st.text_input("📂 Catégorie Amazon", placeholder="Ex: Santé & Soins du corps")
        prix = st.number_input("💰 Prix (€)", min_value=0.0, value=25.0, step=0.5)
        nb_avis = st.number_input("⭐ Nombre d'avis", min_value=0, value=0, step=1)
        note = st.slider("⭐ Note moyenne", 1.0, 5.0, 4.0, 0.1)
        nb_images = st.number_input("🖼️ Nombre d'images", min_value=0, max_value=9, value=5)
        a_plus = st.checkbox("✅ A+ Content présent")

    st.markdown("---")

    if st.button("🚀 Lancer l'audit", use_container_width=True, type="primary"):
        if not titre:
            st.warning("Veuillez au minimum renseigner le titre du produit.")
        else:
            bullets = "\n".join([b for b in [bullet1, bullet2, bullet3, bullet4, bullet5] if b.strip()])

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

            with st.spinner("Analyse en cours avec l'IA..."):
                result = appel_groq(prompt)

            if result:
                score = result.get("score_global", 0)
                sections = result.get("sections", {})

                # Score global
                st.markdown("---")
                st.markdown("## 📊 Résultats de l'audit")

                col_score, col_top3 = st.columns([1, 2])
                with col_score:
                    cls = "score-green" if score >= 75 else ("score-orange" if score >= 50 else "score-red")
                    label = "EXCELLENT" if score >= 75 else ("À AMÉLIORER" if score >= 50 else "CRITIQUE")
                    st.markdown(f"""
                    <div class="metric-card" style="text-align:center">
                        <div style="font-size:0.75rem;letter-spacing:2px;color:#6b7a99">SCORE GLOBAL</div>
                        <div class="score-big {cls}">{score}/100</div>
                        <div style="font-size:0.85rem;color:#6b7a99">{label}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_top3:
                    st.markdown("### 🎯 Top 3 actions prioritaires")
                    for i, action in enumerate(result.get("top3_actions", []), 1):
                        st.markdown(f"**{i}.** {action}")

                # Sections
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
                    cls = score_color(sc, mx)

                    with cols[i % 2]:
                        st.markdown(f"""
                        <div class="metric-card">
                          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                            <span style="font-weight:700">{label}</span>
                            <span class="{cls}" style="font-size:1.1rem;font-weight:800">{sc}/{mx}</span>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                        afficher_reco(items)
                        st.markdown("")

                # Suggestions IA
                st.markdown("---")
                st.markdown("### 💡 Suggestions IA")
                col_t, col_b = st.columns(2)
                with col_t:
                    st.markdown("**Titre optimisé suggéré :**")
                    st.info(result.get("titre_optimise", "—"))
                with col_b:
                    st.markdown("**Bullet point amélioré :**")
                    st.info(result.get("bullet_optimise", "—"))

# ── MODE GÉNÉRATION ────────────────────────────────────────────────────────────
elif mode == "✍️ Générer une fiche":
    st.title("✍️ Générateur de Fiche Produit Amazon")
    st.markdown("Renseignez les informations de base et l'IA génère une fiche optimisée pour Amazon France.")
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

Règles importantes :
- Le titre doit contenir les 2-3 premiers mots-clés naturellement
- Chaque bullet commence par un bénéfice en MAJUSCULES suivi de " — " puis l'explication
- La description doit être persuasive et rassurante
- Optimisé pour Amazon.fr"""

            with st.spinner("Génération en cours avec l'IA..."):
                result_gen = appel_groq(prompt_gen)

            if result_gen:
                st.markdown("---")
                st.markdown("## 📋 Fiche générée")
                st.success("✅ Fiche générée avec succès ! Copiez chaque section dans Seller Central.")

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
                st.text_area("Mots-clés backend (à coller dans Seller Central → Mots-clés)",
                             value=result_gen.get("mots_cles_backend", ""), height=80)

                # Export
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
