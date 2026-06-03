import requests
import random
import time
from bs4 import BeautifulSoup


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def get_product_data(asin, marketplace="fr", retries=3):
    """Scrape la fiche Amazon avec retry automatique."""
    url = f"https://www.amazon.{marketplace}/dp/{asin}"

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=get_headers(), timeout=15)

            if response.status_code == 503:
                time.sleep(2 + attempt)
                continue

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, "html.parser")

            # Vérifier si Amazon bloque
            if "robot" in response.text.lower() or "captcha" in response.text.lower():
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                raise Exception("Amazon bloque la requête (captcha détecté)")

            # ── Titre ──────────────────────────────────────────────────────
            title = ""
            title_tag = soup.find(id="productTitle")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # ── Bullet points ──────────────────────────────────────────────
            bullets = []
            for li in soup.select("#feature-bullets ul li span.a-list-item"):
                txt = li.get_text(strip=True)
                if txt and len(txt) > 5:
                    bullets.append(txt)
            # Fallback
            if not bullets:
                for li in soup.select("#feature-bullets li"):
                    txt = li.get_text(strip=True)
                    if txt and len(txt) > 5:
                        bullets.append(txt)

            # ── Images ─────────────────────────────────────────────────────
            images = soup.select("#altImages li.item img")
            if not images:
                images = soup.select("#altImages img")
            image_count = len(images)

            # ── Note ───────────────────────────────────────────────────────
            rating = None
            rating_tag = soup.select_one("span.a-icon-alt")
            if rating_tag:
                try:
                    rating = float(rating_tag.text.replace(",", ".").split()[0])
                except:
                    pass
            if not rating:
                rating_tag2 = soup.select_one("#acrPopover span.a-icon-alt")
                if rating_tag2:
                    try:
                        rating = float(rating_tag2.text.replace(",", ".").split()[0])
                    except:
                        pass

            # ── Nombre d'avis ──────────────────────────────────────────────
            nb_avis = 0
            avis_tag = soup.select_one("#acrCustomerReviewText")
            if avis_tag:
                try:
                    nb_avis = int(avis_tag.text.strip().replace("\xa0", "").replace(" ", "").replace(",", "").split()[0])
                except:
                    pass

            # ── Prix ───────────────────────────────────────────────────────
            prix = None
            for selector in [".a-price .a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice", ".a-price-whole"]:
                prix_tag = soup.select_one(selector)
                if prix_tag:
                    try:
                        prix_text = prix_tag.get_text(strip=True).replace("€", "").replace(",", ".").replace("\xa0", "").strip()
                        prix = float(prix_text.split(".")[0] + "." + prix_text.split(".")[1][:2]) if "." in prix_text else float(prix_text)
                        break
                    except:
                        pass

            # ── Description ────────────────────────────────────────────────
            description = ""
            desc_tag = soup.select_one("#productDescription p")
            if desc_tag:
                description = desc_tag.get_text(strip=True)
            if not description:
                desc_tag2 = soup.select_one("#productDescription")
                if desc_tag2:
                    description = desc_tag2.get_text(strip=True)[:500]

            # ── A+ Content ─────────────────────────────────────────────────
            a_plus = bool(
                soup.select_one("#aplus") or
                soup.select_one("#aplus3p_feature_div") or
                soup.select_one(".aplus-v2")
            )

            # ── Catégorie ──────────────────────────────────────────────────
            categorie = ""
            breadcrumb = soup.select("#wayfinding-breadcrumbs_feature_div a")
            if breadcrumb:
                categorie = " > ".join([b.get_text(strip=True) for b in breadcrumb[:3]])

            # ── Marque ─────────────────────────────────────────────────────
            marque = ""
            marque_tag = soup.select_one("#bylineInfo")
            if marque_tag:
                marque = marque_tag.get_text(strip=True).replace("Marque :", "").replace("Visiter la boutique", "").strip()

            return {
                "asin": asin,
                "title": title,
                "bullets": bullets,
                "image_count": image_count,
                "rating": rating,
                "nb_avis": nb_avis,
                "prix": prix,
                "description": description,
                "a_plus": a_plus,
                "categorie": categorie,
                "marque": marque,
                "url": url,
            }

        except Exception as e:
            if attempt == retries - 1:
                raise Exception(f"Échec après {retries} tentatives : {e}")
            time.sleep(2)

    raise Exception("Impossible de récupérer la fiche")


def audit_listing(data, mot_cle_principal=""):
    """Scoring avancé avec pondération par section."""
    score = 0
    details = {
        "titre": {"score": 0, "max": 25, "items": []},
        "images": {"score": 0, "max": 20, "items": []},
        "bullets": {"score": 0, "max": 20, "items": []},
        "seo": {"score": 0, "max": 20, "items": []},
        "preuve_sociale": {"score": 0, "max": 15, "items": []},
    }

    # ── TITRE (25 pts) ─────────────────────────────────────────────────────────
    title = data.get("title", "")
    title_len = len(title)
    titre_score = 0

    if title_len >= 150:
        titre_score += 10
        details["titre"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Longueur optimale ({title_len} caractères)"})
    elif title_len >= 80:
        titre_score += 7
        details["titre"]["items"].append({"icon": "⚠️", "type": "warn", "texte": f"Titre correct mais peut être enrichi ({title_len} car.)"})
    else:
        titre_score += 3
        details["titre"]["items"].append({"icon": "❌", "type": "ko", "texte": f"Titre trop court ({title_len} car.) — visez 150+"})

    if data.get("marque") and data["marque"].lower() in title.lower():
        titre_score += 5
        details["titre"]["items"].append({"icon": "✅", "type": "ok", "texte": "Marque présente dans le titre"})
    else:
        details["titre"]["items"].append({"icon": "⚠️", "type": "warn", "texte": "Marque absente du titre"})

    if mot_cle_principal and mot_cle_principal.lower() in title.lower():
        titre_score += 10
        details["titre"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Mot-clé principal '{mot_cle_principal}' présent"})
    elif mot_cle_principal:
        details["titre"]["items"].append({"icon": "❌", "type": "ko", "texte": f"Mot-clé principal '{mot_cle_principal}' absent du titre"})
        titre_score += 2

    details["titre"]["score"] = min(titre_score, 25)

    # ── IMAGES (20 pts) ────────────────────────────────────────────────────────
    img_count = data.get("image_count", 0)
    img_score = 0

    if img_count >= 7:
        img_score = 20
        details["images"]["items"].append({"icon": "✅", "type": "ok", "texte": f"{img_count} images — excellent !"})
    elif img_count >= 5:
        img_score = 14
        details["images"]["items"].append({"icon": "⚠️", "type": "warn", "texte": f"{img_count} images — ajoutez des images lifestyle/comparatives"})
    elif img_count >= 3:
        img_score = 8
        details["images"]["items"].append({"icon": "❌", "type": "ko", "texte": f"Seulement {img_count} images — visez 7 minimum"})
    else:
        img_score = 3
        details["images"]["items"].append({"icon": "❌", "type": "ko", "texte": "Pas assez d'images — très pénalisant"})

    if not data.get("a_plus"):
        details["images"]["items"].append({"icon": "❌", "type": "ko", "texte": "Pas de A+ Content — perd 15-20% de conversion"})
    else:
        img_score = min(img_score + 3, 20)
        details["images"]["items"].append({"icon": "✅", "type": "ok", "texte": "A+ Content présent ✨"})

    details["images"]["score"] = img_score

    # ── BULLETS (20 pts) ───────────────────────────────────────────────────────
    bullet_count = len(data.get("bullets", []))
    bullet_score = 0

    if bullet_count >= 5:
        bullet_score += 15
        details["bullets"]["items"].append({"icon": "✅", "type": "ok", "texte": f"{bullet_count} bullet points — complet"})
    elif bullet_count >= 3:
        bullet_score += 10
        details["bullets"]["items"].append({"icon": "⚠️", "type": "warn", "texte": f"{bullet_count} bullets — ajoutez-en {5 - bullet_count} de plus"})
    else:
        bullet_score += 4
        details["bullets"]["items"].append({"icon": "❌", "type": "ko", "texte": "Bullets insuffisants — Amazon recommande 5"})

    # Longueur moyenne des bullets
    if data.get("bullets"):
        avg_len = sum(len(b) for b in data["bullets"]) / len(data["bullets"])
        if avg_len >= 100:
            bullet_score += 5
            details["bullets"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Bullets détaillés ({int(avg_len)} car. en moyenne)"})
        else:
            details["bullets"]["items"].append({"icon": "⚠️", "type": "warn", "texte": "Bullets trop courts — développez les bénéfices"})

    details["bullets"]["score"] = min(bullet_score, 20)

    # ── SEO (20 pts) ───────────────────────────────────────────────────────────
    seo_score = 0

    if description := data.get("description", ""):
        seo_score += 10
        details["seo"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Description présente ({len(description)} car.)"})
        if mot_cle_principal and mot_cle_principal.lower() in description.lower():
            seo_score += 3
            details["seo"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Mot-clé principal présent dans la description"})
    else:
        details["seo"]["items"].append({"icon": "❌", "type": "ko", "texte": "Description absente — perd 30% de visibilité SEO"})

    if data.get("a_plus"):
        seo_score += 5
        details["seo"]["items"].append({"icon": "✅", "type": "ok", "texte": "A+ Content booste le référencement"})

    if mot_cle_principal:
        bullets_text = " ".join(data.get("bullets", []))
        if mot_cle_principal.lower() in bullets_text.lower():
            seo_score += 2
            details["seo"]["items"].append({"icon": "✅", "type": "ok", "texte": "Mot-clé présent dans les bullets"})
        else:
            details["seo"]["items"].append({"icon": "❌", "type": "ko", "texte": f"Mot-clé '{mot_cle_principal}' absent des bullets"})

    details["seo"]["score"] = min(seo_score, 20)

    # ── PREUVE SOCIALE (15 pts) ────────────────────────────────────────────────
    preuve_score = 0
    nb_avis = data.get("nb_avis", 0)
    rating = data.get("rating", 0)

    if nb_avis >= 500:
        preuve_score += 8
        details["preuve_sociale"]["items"].append({"icon": "✅", "type": "ok", "texte": f"{nb_avis} avis — excellent volume"})
    elif nb_avis >= 100:
        preuve_score += 5
        details["preuve_sociale"]["items"].append({"icon": "⚠️", "type": "warn", "texte": f"{nb_avis} avis — correct, visez 500+"})
    elif nb_avis >= 20:
        preuve_score += 3
        details["preuve_sociale"]["items"].append({"icon": "⚠️", "type": "warn", "texte": f"Seulement {nb_avis} avis — stimulez les avis"})
    else:
        details["preuve_sociale"]["items"].append({"icon": "❌", "type": "ko", "texte": f"Très peu d'avis ({nb_avis}) — priorité absolue"})

    if rating:
        if rating >= 4.5:
            preuve_score += 7
            details["preuve_sociale"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Note excellente : {rating}/5 ⭐"})
        elif rating >= 4.0:
            preuve_score += 5
            details["preuve_sociale"]["items"].append({"icon": "✅", "type": "ok", "texte": f"Bonne note : {rating}/5"})
        elif rating >= 3.5:
            preuve_score += 2
            details["preuve_sociale"]["items"].append({"icon": "⚠️", "type": "warn", "texte": f"Note moyenne : {rating}/5 — travaillez la satisfaction"})
        else:
            details["preuve_sociale"]["items"].append({"icon": "❌", "type": "ko", "texte": f"Note faible : {rating}/5 — urgence !"})
    else:
        details["preuve_sociale"]["items"].append({"icon": "⚠️", "type": "warn", "texte": "Note non récupérée"})

    details["preuve_sociale"]["score"] = min(preuve_score, 15)

    # ── SCORE GLOBAL ───────────────────────────────────────────────────────────
    score_global = sum(s["score"] for s in details.values())

    # Top 3 recommandations
    top3 = []
    if details["titre"]["score"] < 18:
        top3.append("Optimiser le titre avec le mot-clé principal en début")
    if details["seo"]["score"] < 12:
        top3.append("Ajouter une description complète avec mots-clés")
    if details["images"]["score"] < 14:
        top3.append("Atteindre 7 images + ajouter A+ Content")
    if details["bullets"]["score"] < 14:
        top3.append("Enrichir les bullet points (bénéfices + mots-clés)")
    if details["preuve_sociale"]["score"] < 10:
        top3.append("Stimuler les avis clients (email follow-up, insert produit)")

    return {
        "score_global": score_global,
        "details": details,
        "top3": top3[:3],
    }


if __name__ == "__main__":
    asin = input("ASIN : ").strip()
    mot_cle = input("Mot-clé principal (optionnel) : ").strip()

    try:
        product = get_product_data(asin)
        result = audit_listing(product, mot_cle)

        print("\n===== DONNÉES RÉCUPÉRÉES =====")
        print(f"Titre       : {product['title'][:80]}...")
        print(f"Longueur    : {len(product['title'])} car.")
        print(f"Images      : {product['image_count']}")
        print(f"Bullets     : {len(product['bullets'])}")
        print(f"Note        : {product['rating']}")
        print(f"Avis        : {product['nb_avis']}")
        print(f"Prix        : {product['prix']}€")
        print(f"Description : {'Oui' if product['description'] else 'Non'}")
        print(f"A+ Content  : {'Oui' if product['a_plus'] else 'Non'}")
        print(f"Catégorie   : {product['categorie']}")

        print(f"\n===== SCORE : {result['score_global']}/100 =====")
        for section, data_s in result["details"].items():
            print(f"  {section.capitalize():<15} : {data_s['score']}/{data_s['max']}")

        print("\nTop 3 actions :")
        for i, r in enumerate(result["top3"], 1):
            print(f"  {i}. {r}")

    except Exception as e:
        print("Erreur :", e)
