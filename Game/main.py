"""
Jeu d'enquête interactif avec interface web (Flask)
-------------------------------------------------
Trois suspects (IA Gemma ou simulateurs) sont interrogés via une interface web.
Le joueur peut poser des questions, cliquer sur un suspect, et accuser l'un d'eux.
Si l'accusation est correcte, le meurtrier avoue. Sinon, la partie redémarre avec un nouveau scénario.
"""

from flask import Flask, render_template, request, jsonify
import random
import requests
import time

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"

# ------------------ Trames de base ------------------
TRAMES = [
    {
        "context": "Un meurtre a eu lieu dans un manoir isolé lors d'une tempête.",
        "metiers": ["chef cuisinier", "médecin", "peintre"],
    },
    {
        "context": "Une disparition mystérieuse dans un train de nuit.",
        "metiers": ["conducteur", "journaliste", "comédien"],
    },
    {
        "context": "Un crime dans une station de recherche polaire.",
        "metiers": ["scientifique", "technicien", "infirmier"],
    }
]

TRAME_INNOCENT = (
    "Tu es {name}, {age} ans, {metier}.\n"
    "Personnalité: {personnalite}.\n"
    "Alibi: {alibi}.\n"
    "Contexte: {context}\n"
    "Consignes de style :\n"
    "- Quand tu décris tes actions, gestes ou émotions, parle à la 3ᵉ personne.\n"
    "- Quand tu parles au joueur (dialogue), parle à la 1ʳᵉ personne.\n"
    "- Tu es suspect(e), mais innocent(e). Réponds comme ton personnage le ferait."
)

TRAME_MEURTRIER = (
    "Tu es {name}, {age} ans, {metier}.\n"
    "Personnalité: {personnalite}.\n"
    "Alibi: {alibi}.\n"
    "Contexte: {context}\n"
    "Consignes de style :\n"
    "- Quand tu décris tes actions, gestes ou émotions, parle à la 3ᵉ personne.\n"
    "- Quand tu parles au joueur (dialogue), parle à la 1ʳᵉ personne.\n"
    "- Tu es le MEURTRIER. Tu dois cacher ta culpabilité et rester crédible."
)


# ------------------ Utilitaires ------------------
def call_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False  # important: on veut une seule réponse JSON
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=30)
    data = r.json()
    return data.get("response") or data.get("output", [{"content": "(aucune réponse)"}])[0].get("content", "(aucune réponse)")


def simulate_response(name, murderer, question):
    base = f"{name}: "
    if murderer:
        base += random.choice([
            "Je ne vois pas pourquoi je serais accusé...",
            "C'est ridicule, je n'ai rien fait.",
            "Je pense que vous perdez votre temps."
        ])
    else:
        base += random.choice([
            "Je n'ai rien vu, j'étais ailleurs.",
            "Je ne connaissais pas la victime.",
            "Je vous jure, je n'ai rien fait."
        ])
    if "où" in question.lower():
        base += " J'étais dans un autre endroit au moment du crime."
    return base

# ------------------ Classe Agent ------------------
class Agent:
    def __init__(self, nom, prompt_initial, murderer=False, use_ollama=False):
        self.nom = nom
        self.prompt_initial = prompt_initial
        self.murderer = murderer
        self.use_ollama = use_ollama
        self.history = []

    def repondre(self, question):
        prompt = self.prompt_initial + "\n" + "\n".join(self.history[-6:]) + f"\nJoueur: {question}\n{self.nom}:"
        if self.use_ollama:
            try:
                response = call_ollama(prompt)
            except Exception as e:
                print("Erreur Ollama :", e)
                response = simulate_response(self.nom, self.murderer, question)
        else:
            response = simulate_response(self.nom, self.murderer, question)
        self.history.append(f"Joueur: {question}")
        self.history.append(f"{self.nom}: {response}")
        return response

# ------------------ Génération d'un scénario ------------------
def generer_scenario(use_ollama=False):
    t = random.choice(TRAMES)
    context = t['context']
    roles = random.sample(t['metiers'], 3)
    murderer_index = random.randint(0, 2)

    # --- Génération de la victime ---
    victime_prenoms = ["Clara", "Luc", "Élodie", "Martin", "Sophie", "Nicolas"]
    victime_noms = ["Morel", "Durand", "Petit", "Garcia", "Bernard", "Roux"]
    victime_metiers = ["journaliste", "commerçant", "professeur", "critique d’art", "chercheur", "photographe"]
    victime_nom = f"{random.choice(victime_prenoms)} {random.choice(victime_noms)}"
    victime_age = random.randint(28, 50)
    victime_metier = random.choice(victime_metiers)
    cause_mort = random.choice([
        "a été frappé à la tête avec un objet lourd",
        "a été empoisonné pendant le dîner",
        "a été poignardé dans le dos",
        "a été retrouvé étranglé dans le bureau",
        "a été découvert mort dans la bibliothèque, sans trace d’effraction"
    ])

    # --- Lien entre la victime et les suspects ---
    relations_possibles = [
        "travaillait pour la victime depuis plusieurs années",
        "était un ami proche de la victime",
        "avait eu une dispute récente avec la victime",
        "devait de l'argent à la victime",
        "était souvent en désaccord avec la victime"
    ]

    persos = []
    presentation = (
        f"🕯️ Nouvelle enquête :\n\n"
        f"{context}\n\n"
        f"La victime est **{victime_nom}**, {victime_age} ans, {victime_metier}. "
        f"Elle {cause_mort}.\n\n"
        f"Les suspects sont :\n"
    )

    for i, nom in enumerate(["Ariane", "Benoit", "Camille"]):
        metier = roles[i]
        age = random.randint(25, 50)
        personnalite = random.choice([
            "calme et observateur", "bavard et sûr de lui", "nerveux et curieux"
        ])
        relation = random.choice(relations_possibles)
        alibi = random.choice([
            "était seul dans sa chambre", "travaillait tard", "était dehors à fumer"
        ])

        if i == murderer_index:
            prompt = TRAME_MEURTRIER.format(
                name=nom, age=age, metier=metier, personnalite=personnalite,
                alibi=alibi, context=f"{context}\nLa victime était {victime_nom}, {victime_metier}. Tu {relation}."
            )
            murderer = True
        else:
            prompt = TRAME_INNOCENT.format(
                name=nom, age=age, metier=metier, personnalite=personnalite,
                alibi=alibi, context=f"{context}\nLa victime était {victime_nom}, {victime_metier}. Tu {relation}."
            )
            murderer = False

        persos.append(Agent(nom, prompt, murderer, use_ollama))
        presentation += f"• {nom}, {age} ans, {metier}, {personnalite} — {relation}.\n"

    presentation += "\nÀ vous de poser vos questions pour découvrir la vérité…"

    return persos, murderer_index, presentation



# ------------------ Variables globales ------------------
agents = []
murderer_index = None
context_actuel = None
use_ollama = True
notes = {}  # clé = nom du suspect ou 'victime', valeur = texte

# ------------------ Routes Flask ------------------
@app.route('/')
def index():
    global agents, murderer_index, context_actuel
    agents, murderer_index, context_actuel = generer_scenario(use_ollama)
    noms = [a.nom for a in agents]
    return render_template('index.html', suspects=noms, context=context_actuel)

@app.route('/note', methods=['POST'])
def add_note():
    data = request.get_json()
    sujet = data.get('sujet')  # nom du suspect ou 'victime'
    texte = data.get('texte')
    if sujet:
        notes[sujet] = texte
    return jsonify({"status": "ok", "notes": notes})

# Récupérer toutes les notes
@app.route('/notes', methods=['GET'])
def get_notes():
    return jsonify({"notes": notes})

@app.route('/question', methods=['POST'])
def question():
    data = request.get_json()
    nom = data.get('nom')
    question = data.get('question')
    agent = next((a for a in agents if a.nom == nom), None)
    if not agent:
        return jsonify({"reponse": "Suspect inconnu."})
    reponse = agent.repondre(question)
    return jsonify({"reponse": reponse})

@app.route('/accuser', methods=['POST'])
def accuser():
    data = request.get_json()
    nom = data.get('nom')
    global murderer_index, agents
    vrai_nom = agents[murderer_index].nom
    if nom == vrai_nom:
        return jsonify({"resultat": "gagné", "message": f"Bravo ! {nom} était bien le meurtrier et il avoue tout !"})
    else:
        agents[:], murderer_index, context = generer_scenario(use_ollama)
        return jsonify({"resultat": "perdu", "message": f"Non, {nom} était innocent... Le jeu recommence avec une nouvelle enquête !"})

if __name__ == '__main__':
    app.run(debug=True)