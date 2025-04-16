import requests
from django.shortcuts import redirect

API_REFRESH_URL = "https://syrif.bcrg-guinee.org:8186/auth/refresh"

def refresh_token(session):
    """
    Fonction pour rafraîchir le token d'accès en utilisant le refreshToken.
    """
    refresh_token = session.get("refreshToken")

    if not refresh_token:
        return None  # Pas de refreshToken -> l'utilisateur doit se reconnecter

    headers = {"Content-Type": "application/json"}
    data = {"refreshToken": refresh_token}

    try:
        response = requests.post(API_REFRESH_URL, json=data, headers=headers)

        if response.status_code == 200:
            new_tokens = response.json()
          
            # Mise à jour des tokens dans la session
            session["token"] = new_tokens.get("accessToken")
            session["refreshToken"] = new_tokens.get("refreshToken")

            return new_tokens.get("accessToken")  # Retourne le nouveau token d'accès
        else:
            return None  # Si le refreshToken est invalide, il faut se reconnecter
    except requests.exceptions.RequestException:
        return None
