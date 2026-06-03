import streamlit as st
import os
import json
import re
from groq import Groq
from audit_listing import get_product_data, audit_listing

st.set_page_config(page_title="Fiche Pro — Audit & Génération", layout="wide", page_icon="📦")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY)

# ── CSS THÈME CLAIR ────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f8f9fb; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5e7eb; }
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
st.sidebar.title("📦 Fiche Pro")
st.sidebar.markdown("---")
mode = st.sidebar.radio("Mode", ["🔍 Audit de fiche", "✍️ Générer une fiche"])
st.sidebar.markdown("---")
st.sidebar.markdown("🔗 [Ads Optimizer Pro](https://amazon-optimizer-rwjs.onrender.com)")
st.sidebar.markdown("*by AilteqFrance*")

# ── FONCTIONS ──────────────────────────────────────────────────────────────────
def extract_asin(input_text):
    input_text = input_text.strip()
    if re.match(r'^[A-Z0-9]{10}$', input_text):
        return input_text
    match = re.search(r'/dp/([A-Z0-9]{10})', input_text)
    if match:
        return match.group(1)
    match = re.search(r'/gp/product/([A-Z0-9]{10})', input_text)
    if match:
        return match.group(1)
    return None

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

def afficher_resultats_audit(result, product_data=None):
    score = result.get("score_global", 0)
    details = result.get("details", {})

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
        for i, action in enumerate(result.get("top3", []), 1):
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
        sec = details.get(key, {})
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

    # Suggestions IA
    if product_data:
        st.markdown("---")
        st.markdown("### 💡 Suggestions IA")
        with st.spinner("Génération des suggestions..."):
            prompt = f"""Tu es un expert Amazon. Propose en JSON :
{{
  "titre_optimise": "<titre optimisé>",
  "bullet_optimise": "<bullet 1 amélioré>"
}}

Titre actuel : {product_data.get('title', '')}
Bullet 1 : {product_data.get('bullets', [''])[0] if product_data.get('bullets') else ''}
Score SEO : {details.get('seo', {}).get('score', 0)}/20"""
            suggestions = appel_groq(prompt)

        if suggestions:
            col_t, col_b = st.columns(2)
            with col_t:
                st.markdown("**Titre optimisé suggéré :**")
                st.info(suggestions.get("titre_optimise", "—"))
            with col_b:
                st.markdown("**Bullet point amélioré :**")
                st.info(suggestions.get("bullet_optimise", "—"))

# ── MODE AUDIT ─────────────────────────────────────────────────────────────────
if mode == "🔍 Audit de fiche":
    st.title("🔍 Audit de Fiche Produit Amazon")
    st.markdown("Entrez un ASIN ou URL Amazon — les données sont récupérées automatiquement.")
    st.markdown("---")

    col_asin, col_mkt = st.columns([3, 1])
    with col_asin:
        asin_input = st.text_input("ASIN ou URL Amazon", placeholder="Ex: B09XPQRCW7 ou https://www.amazon.fr/dp/B09XPQRCW7")
    with col_mkt:
        marketplace = st.selectbox("Marketplace", ["fr", "com", "co.uk", "de", "es", "it"])

    mot_cle_principal = st.text_input("🔑 Mot-clé principal cible (optionnel)", placeholder="Ex: kit santé 3en1")

    if "product_data" not in st.session_state:
        st.session_state.product_data = None

    col_fetch, _ = st.columns([2, 2])
    with col_fetch:
        if st.button("🔄 Récupérer la fiche Amazon", use_container_width=True):
            asin = extract_asin(asin_input)
            if not asin:
                st.error("ASIN invalide — ex: B09XPQRCW7")
            else:
                with st.spinner(f"Récupération de la fiche {asin}..."):
                    try:
                        data = get_product_data(asin, marketplace)
                        st.session_state.product_data = data
                        st.success(f"✅ Fiche récupérée — {data.get('title', '')[:60]}...")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # Afficher données récupérées
    if st.session_state.product_data:
        pd = st.session_state.product_data
        st.markdown("---")
        st.markdown("### 📋 Données récupérées")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🖼️ Images", pd.get("image_count", 0))
        col2.metric("⭐ Note", pd.get("rating", "—"))
        col3.metric("💬 Avis", pd.get("nb_avis", 0))
        col4.metric("💰 Prix", f"{pd.get('prix', '—')}€" if pd.get('prix') else "—")

        with st.expander("Voir les détails complets"):
            st.write(f"**Titre :** {pd.get('title', '')}")
            st.write(f"**Catégorie :** {pd.get('categorie', '—')}")
            st.write(f"**Marque :** {pd.get('marque', '—')}")
            st.write(f"**A+ Content :** {'✅ Oui' if pd.get('a_plus') else '❌ Non'}")
            st.write(f"**Description :** {pd.get('description', '—')[:200]}...")
            st.write(f"**Bullets ({len(pd.get('bullets', []))}) :**")
            for b in pd.get("bullets", []):
                st.write(f"  • {b[:100]}")

        st.markdown("---")
        if st.button("🚀 Lancer l'audit", use_container_width=True, type="primary"):
            with st.spinner("Analyse en cours..."):
                result = audit_listing(pd, mot_cle_principal)
            afficher_resultats_audit(result, pd)

    elif not asin_input:
        st.info("👆 Entrez un ASIN ou une URL Amazon pour commencer")

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

Retourne UNIQUEMENT un JSON valide :
{{
  "titre": "<titre optimisé max 200 caractères>",
  "bullet1": "<bullet 1 — BÉNÉFICE EN MAJUSCULES — explication>",
  "bullet2": "<bullet 2>",
  "bullet3": "<bullet 3>",
  "bullet4": "<bullet 4>",
  "bullet5": "<bullet 5>",
  "description": "<description 2000 car. max>",
  "mots_cles_backend": "<mots-clés séparés par espaces, max 250 octets>"
}}

Produit : {produit}
Catégorie : {categorie_gen or 'non spécifiée'}
Prix : {prix_gen}€
Mots-clés : {mots_cles or 'non spécifiés'}
Avantages : {avantages or 'non spécifiés'}
Public : {public_cible or 'non spécifié'}"""

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
