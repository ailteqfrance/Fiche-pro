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


def generer_rapport_pdf(product_data, audit_result, suggestions):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    VERT = colors.HexColor("#059669")
    ROUGE = colors.HexColor("#dc2626")
    ORANGE = colors.HexColor("#d97706")
    GRIS = colors.HexColor("#f9fafb")

    styles = getSampleStyleSheet()
    titre_s = ParagraphStyle("titre", fontSize=18, textColor=VERT, spaceAfter=4, fontName="Helvetica-Bold", alignment=TA_CENTER)
    sous_titre_s = ParagraphStyle("sous", fontSize=9, textColor=colors.HexColor("#6b7280"), spaceAfter=12, alignment=TA_CENTER)
    h2_s = ParagraphStyle("h2", fontSize=12, textColor=VERT, spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold")
    h3_s = ParagraphStyle("h3", fontSize=10, textColor=colors.HexColor("#111827"), spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold")
    normal_s = ParagraphStyle("normal", fontSize=8, textColor=colors.HexColor("#374151"), spaceAfter=3)
    small_s = ParagraphStyle("small", fontSize=7, textColor=colors.HexColor("#6b7280"), spaceAfter=2)
    footer_s = ParagraphStyle("footer", fontSize=7, textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER, spaceBefore=20)

    story = []

    # Header
    story.append(Paragraph("Audit Fiche Produit Amazon", titre_s))
    story.append(Paragraph(f"ASIN : {product_data.get('asin', '—')} — {product_data.get('categorie', '')}", sous_titre_s))
    story.append(HRFlowable(width="100%", thickness=2, color=VERT, spaceAfter=10))

    # Score global
    score = audit_result.get("score_global", 0)
    score_color = VERT if score >= 75 else (ORANGE if score >= 50 else ROUGE)
    label = "EXCELLENT" if score >= 75 else ("A AMELIORER" if score >= 50 else "CRITIQUE")

    score_data = [["SCORE GLOBAL", f"{score}/100", label]]
    score_table = Table(score_data, colWidths=[5*cm, 4*cm, 6*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GRIS),
        ("FONTNAME", (0,0), (0,0), "Helvetica-Bold"),
        ("FONTNAME", (1,0), (1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (1,0), (1,0), score_color),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 10))

    # Titre produit
    story.append(Paragraph("Fiche analysee", h2_s))
    titre_prod = product_data.get("title", "")[:120] + ("..." if len(product_data.get("title","")) > 120 else "")
    story.append(Paragraph(titre_prod, normal_s))

    kpi_data = [["Images", "Note", "Avis", "Prix", "A+ Content"],
                [str(product_data.get("image_count",0)),
                 str(product_data.get("rating","—")),
                 str(product_data.get("nb_avis",0)),
                 f"{product_data.get('prix','—')}EUR",
                 "Oui" if product_data.get("a_plus") else "Non"]]
    kpi_table = Table(kpi_data, colWidths=[3*cm]*5)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), VERT),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 6))
    story.append(kpi_table)

    # Scores par section
    story.append(Paragraph("Scores par section", h2_s))
    details = audit_result.get("details", {})
    section_labels = {"titre": "Titre", "images": "Images", "bullets": "Bullet Points", "seo": "SEO", "preuve_sociale": "Preuve Sociale"}
    sec_data = [["Section", "Score", "Max", "Statut"]]
    for key, label_s in section_labels.items():
        sec = details.get(key, {})
        sc = sec.get("score", 0)
        mx = sec.get("max", 20)
        pct = sc/mx*100
        statut = "Excellent" if pct >= 75 else ("A ameliorer" if pct >= 50 else "Critique")
        sec_data.append([label_s, str(sc), str(mx), statut])
    sec_table = Table(sec_data, colWidths=[5*cm, 2.5*cm, 2.5*cm, 5*cm])
    sec_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GRIS]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("ALIGN", (1,0), (2,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(sec_table)

    # Top 3 actions
    story.append(Paragraph("Top 3 actions prioritaires", h2_s))
    for i, action in enumerate(audit_result.get("top3", []), 1):
        story.append(Paragraph(f"{i}. {action}", normal_s))

    # Titres optimisés
    if suggestions:
        story.append(Paragraph("Titres optimises", h2_s))
        story.append(Paragraph("Version PC (180-200 car.) :", h3_s))
        story.append(Paragraph(suggestions.get("titre_pc", "—"), normal_s))
        story.append(Paragraph("Version Mobile (max 80 car.) :", h3_s))
        story.append(Paragraph(suggestions.get("titre_mobile", "—"), normal_s))

        # Bullets optimisés
        story.append(Paragraph("Bullet Points optimises - Version PC", h2_s))
        for i, bp in enumerate(suggestions.get("bullets_pc", []), 1):
            story.append(Paragraph(f"{i}. {bp[:300]}", normal_s))

        story.append(Paragraph("Bullet Points optimises - Version Mobile", h2_s))
        for i, bp in enumerate(suggestions.get("bullets_mobile", []), 1):
            story.append(Paragraph(f"{i}. {bp[:200]}", normal_s))

        # Mots interdits
        mots = suggestions.get("mots_interdits_detectes", [])
        if mots:
            story.append(Paragraph("Mots interdits detectes", h2_s))
            for m in mots:
                story.append(Paragraph(f"- {m}", normal_s))

        # Conseil expert
        story.append(Paragraph("Conseil Expert", h2_s))
        story.append(Paragraph(suggestions.get("conseil_expert", "—"), normal_s))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"), spaceBefore=15))
    story.append(Paragraph("Rapport genere par Fiche Pro — AilteqFrance", footer_s))

    doc.build(story)
    buf.seek(0)
    return buf.read()


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

    # Suggestions IA + PDF
    if product_data:
        st.markdown("---")
        st.markdown("### 💡 Optimisations IA — Expert Fiche Produit")

        with st.spinner("Generation des optimisations par l'IA..."):
            bullets_actuels = "\n".join([f"{i+1}. {b}" for i, b in enumerate(product_data.get('bullets', []))])
            titre_actuel = product_data.get('title', '')
            marque_actuel = product_data.get('marque', '')
            categorie_actuel = product_data.get('categorie', '')
            rating_actuel = product_data.get('rating', '')
            nb_avis_actuel = product_data.get('nb_avis', 0)
            prix_actuel = product_data.get('prix', '')
            score_seo = details.get('seo', {}).get('score', 0)
            score_titre = details.get('titre', {}).get('score', 0)

            prompt = f"""Tu es un expert Amazon senior avec 20 ans d experience en optimisation de fiches produit sur Amazon France. Tu as optimise plus de 5000 fiches et tu sais exactement ce qui convertit.

MISSION : Optimise completement cette fiche produit Amazon. Sois TRES concret, specifique et percutant. Pas de contenu generique.

REGLES STRICTES :
- titre_pc : EXACTEMENT entre 150 et 200 caracteres. Mot-cle principal EN PREMIER. Marque a la fin apres tiret.
- titre_mobile : MAXIMUM 80 caracteres. Le benefice le plus fort en premier mot.
- bullets_pc : CHAQUE bullet MINIMUM 350 caracteres, MAXIMUM 500 caracteres. Format: "MOT-CLE EN MAJUSCULES - benefice principal | detail technique | preuve sociale ou usage concret". Jamais de contenu generique.
- bullets_mobile : CHAQUE bullet entre 150 et 200 caracteres. Benefice immediat + detail cle.
- mots_interdits_detectes : Liste TOUS les mots interdits Amazon trouves dans les bullets/titre actuels (garanti, meilleur, N1, certifie sans preuve, satisfait ou rembourse, ecologique sans label, naturel sans preuve, sans danger, approuve).
- mots_cles_manquants : 5 mots-cles specifiques a forte intention d achat absents de la fiche actuelle.
- analyse_conversion : 3 points CONCRETS et SPECIFIQUES sur ce qui freine la conversion sur cette fiche precise.
- conseil_expert : UN seul conseil ultra-specifique et actionnable pour cette fiche, pas un conseil generique.

EXEMPLE de bullet_pc de qualite :
"ECRANS LCD DOUBLE AFFICHAGE 3.5 POUCES - Lisez vos resultats d un seul coup d oeil grace aux chiffres 2x plus grands que la moyenne du marche, retro-eclaires automatiquement en cas de luminosite insuffisante. Ideal pour les seniors ou toute personne souhaitant eviter les erreurs de lecture - teste et approuve par 847 familles en France."

FICHE A OPTIMISER :
Titre actuel : {titre_actuel}
Marque : {marque_actuel}
Categorie : {categorie_actuel}
Prix : {prix_actuel}EUR
Bullets actuels :
{bullets_actuels}
Note : {rating_actuel}/5 ({nb_avis_actuel} avis)
Images : {product_data.get("image_count", 0)}
A+ Content : {"Oui" if product_data.get("a_plus") else "Non"}

Retourne UNIQUEMENT ce JSON valide, sans commentaire :
{{
  "titre_pc": "...",
  "titre_mobile": "...",
  "bullets_pc": ["bullet1 min 350 car", "bullet2", "bullet3", "bullet4", "bullet5"],
  "bullets_mobile": ["bullet1 mobile 150-200 car", "bullet2", "bullet3", "bullet4", "bullet5"],
  "mots_interdits_detectes": ["mot1", "mot2"],
  "mots_cles_manquants": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "analyse_conversion": "point1. point2. point3.",
  "conseil_expert": "conseil ultra-specifique et actionnable"
}}"""
            suggestions = appel_groq(prompt)

        if suggestions:
            # Titres
            st.markdown("#### 📝 Titres optimisés")
            col_pc, col_mob = st.columns(2)
            with col_pc:
                titre_pc = suggestions.get("titre_pc", "—")
                st.markdown("**🖥️ Version PC (180-200 car.) :**")
                st.info(titre_pc)
                st.caption(f"{len(titre_pc)} caractères")
            with col_mob:
                titre_mob = suggestions.get("titre_mobile", "—")
                st.markdown("**📱 Version Mobile (max 80 car.) :**")
                st.info(titre_mob)
                st.caption(f"{len(titre_mob)} caractères")

            # Bullets
            st.markdown("#### 🎯 Bullet Points optimisés")
            tab_pc, tab_mob = st.tabs(["🖥️ Version PC (jusqu'à 500 car.)", "📱 Version Mobile (max 200 car.)"])
            with tab_pc:
                for i, bp in enumerate(suggestions.get("bullets_pc", []), 1):
                    st.markdown(f"**Bullet {i} :** {bp}")
                    color = "green" if len(bp) <= 500 else "red"
                    st.caption(f":{color}[{len(bp)} caractères]")
            with tab_mob:
                for i, bp in enumerate(suggestions.get("bullets_mobile", []), 1):
                    st.markdown(f"**Bullet {i} :** {bp}")
                    color = "green" if len(bp) <= 200 else "orange"
                    st.caption(f":{color}[{len(bp)} caractères]")

            # Alertes mots interdits
            mots_interdits = suggestions.get("mots_interdits_detectes", [])
            if mots_interdits:
                st.markdown("#### ⚠️ Mots interdits détectés")
                for mot in mots_interdits:
                    st.warning(f"⛔ **{mot}** — à supprimer (risque de suppression de fiche Amazon)")

            # Mots-clés manquants
            mots_manquants = suggestions.get("mots_cles_manquants", [])
            if mots_manquants:
                st.markdown("#### 🔍 Mots-clés opportunités")
                cols_kw = st.columns(min(len(mots_manquants), 3))
                for i, kw in enumerate(mots_manquants):
                    cols_kw[i % 3].info(f"🎯 {kw}")

            # Analyse conversion
            st.markdown("#### 💰 Analyse conversion")
            st.info(suggestions.get("analyse_conversion", "—"))

            # Conseil expert
            st.markdown("#### 🏆 Conseil Expert")
            st.success(f"💡 {suggestions.get('conseil_expert', '—')}")

            # Export PDF
            st.markdown("---")
            st.markdown("#### 📄 Rapport PDF")
            try:
                pdf_bytes = generer_rapport_pdf(product_data, result, suggestions)
                st.download_button(
                    "⬇️ Télécharger le rapport PDF complet",
                    pdf_bytes,
                    f"audit_fiche_{product_data.get('asin', 'asin')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"PDF non disponible : {e}")

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
