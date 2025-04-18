from django.core.mail import EmailMessage
from django.shortcuts import render,redirect
from django.contrib import messages
import json
import openpyxl
import requests
import re # est le module "Regular Expressions" (expressions régulières) de Python. 
from Reporting_BNIG import settings
from Reporting_BNIG.settings import URL_BASE_BCRG
from Reporting.utils import refresh_token
from django.core.mail import send_mail

# page d'accueil
def home(request):
    token = request.session.get("token")
    if not token:
        return redirect('login')
    else:
        user = request.session.get("user")
    return render(request,'Reporting/home.html',{'user': user})

# Fonction de connexion
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "username": username,
            "password": password
        }
        try:
            # Envoie les données en JSON
            response = requests.post("https://syrif.bcrg-guinee.org:8186/auth/signin",
                                     data=json.dumps(data),  # Convertir en JSON
                                     headers=headers)
            if response.status_code == 200:
                token = response.json().get("token")
                user = response.json().get("username")
                password = response.json().get("password")
                request.session["user"] = user
                request.session["token"] = token
                return redirect('home')
            else:
                # Gérer les erreurs de connexion
                if response.status_code == 401:
                    error = "Nom d'utilisateur ou mot de passe incorrect."
                    messages.error(request,error)
                elif response.status_code == 403:
                    error =  "Accès interdit."
                    messages.error(request,error)
                else:
                   error = "Informations incorrectes. veuillez réessayer."
                   messages.error(request,error)
                return redirect('login')
        
        except requests.exceptions.RequestException:

            messages.error(request, "Erreur de connexion verifiez votre connexion internet")
            return redirect('login')
        except ConnectionError:
    # Cas où la connexion au serveur a échoué
            messages.error(request, "Erreur de connexion : Impossible de se connecter au serveur.")
            return redirect('login')

    return render(request, 'Reporting/login.html')

def logout_view(request):
    # Vérifier si l'utilisateur est connecté
    token = request.session.get("token")
    if not token:
        return redirect('login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        token = request.session.get("token")
        # Vérifier si le token existe dans la session
        data = {
            "username": username,
            "password": password
        }
        
        headers = {
                "Content-Type": "application/json"
            }
            
        try:
            response = requests.post("https://syrif.bcrg-guinee.org:8186/auth/logout",
                                    headers=headers,data=json.dumps(data),  # Convertir en JSON
                                    )
            response.raise_for_status()  # Vérifier si la requête a réussi
            # Si la réponse est 401, cela signifie que le token a expiré, donc on le rafraîchit
            if response.status_code == 401:
                new_token = refresh_token(request)
                # Si le rafraîchissement du token réussit, on met à jour la session
                if new_token:
                    token = new_token
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    response = requests.post("https://syrif.bcrg-guinee.org:8186/auth/logout",
                                            headers=headers,data=json.dumps(data),  # Convertir en JSON
                                            )
                    response.raise_for_status()

                    return redirect('logout')
                else:
                    messages.error(request, "Une erreur s'est produite veillez vous reconnecter")
                    # Si le rafraîchissement échoue, rediriger vers la page de connexion
                    return redirect('login')
            # Si la réponse est 200, cela signifie que la déconnexion a réussi
            if response.status_code == 200:
                msg = response.json().get("message")
                
                request.session.flush()  # Supprime toutes les données de la session
                    
                messages.success(request, msg)
                return redirect('login')
            else:
                messages.error(request, "Erreur lors de la déconnexion  informations incorrectes")
                return redirect('logout')
        except requests.exceptions.RequestException:
            messages.error(request, "Erreur de connexion: verifiez votre connexion internet")
            return redirect('logout')

    
    return render(request, 'Reporting/logout.html')
    

# telechargement de fichier


from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UploadExcelForm
from datetime import datetime
import pandas as pd
import requests

def upload_excel(request):
    token = request.session.get("token")
    form = UploadExcelForm()
    if not token:
        return redirect('login')

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    if request.method == 'POST':
        statut = request.POST.get('statut')
        date = request.POST.get('date')

        if not all([statut, date]):
            messages.error(request, "Veuillez remplir tous les champs !")
            return redirect("upload_excel")

        try:
            date_format = datetime.strptime(date, "%Y-%m-%d")
            date_str = date_format.strftime("%Y-%m-%d")
        except ValueError:
            messages.error(request, "Format de date invalide. Utilisez AAAA-MM-JJ.")
            return redirect("upload_excel")

        excel_file = request.FILES['excel_file']
        if not excel_file:
            messages.error(request, "Veuillez importer un fichier !")
            return redirect("upload_excel")

        try:
            dataFile = pd.read_excel(excel_file,sheet_name='BALG_01', header=3)
            dataFile = dataFile.fillna("")  # ✅ Remplace les champs vides par ""
            items_data = []

            for index, row in dataFile.iterrows():
                try:
                    item = {
                        "chapitre": str(row.get('Chapitre', "")),
                        "intituleChapitre": str(row.get('Intitulé chapitre', "")),
                        "codeDevise": str(row.get('Devise', "")),
                        "numCompte": str(row.get('Numéro de Compte', "")),
                        "intituleCompte": str(row.get('Intitulé du compte', "")),
                        "numeroClient": str(row.get('Numéro Client', "")),
                        "nomClient": str(row.get('Nom Client', "")),
                        "soldeDebit": float(row.get('Solde débit DEVISE', 0)),
                        "soldeCredit": float(row.get('Solde crédit DEVISE', 0)),
                        "soldeNet": float(row.get('soldeNet', 0)),
                        "resident": str(row.get('Résident (R / NR)', 'RESIDENT')).upper(),
                        "codeAgentEconomique": str(row.get('Agent économique', "")),
                        "codeSecteurActivite": str(row.get("Secteur d'activité", "")),
                    }
                    items_data.append(item)
                except KeyError as e:
                    messages.error(request, f"Colonne '{e}' manquante à la ligne {index + 2}.")
                    return render(request, 'Reporting/upload_excel.html', {'form': form})
                except Exception as e:
                    messages.error(request, f"Erreur ligne {index + 2}: {e}")
                    return render(request, 'Reporting/upload_excel.html', {'form': form})

            transmission_data = {
                "dateArrete": date_str,
                "statut": statut
            }

            payload = {
                "transmission": transmission_data,
                "versionAPI": "1.0.0",
                "items": items_data,
                "items2": [""]
            }
            print(payload)

            api_url = "https://syrif.bcrg-guinee.org:8186/api/balance"
            try:
                response = requests.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                status_ok = response.json().get('description')
                if status_ok == "Traitement effectué avec succès.":
                    messages.success(request, status_ok)
                else:
                    messages.error(request, status_ok)
                return redirect('upload_excel')
            except requests.exceptions.RequestException as e:
                messages.error(request, f"Erreur API: {e}")
                return redirect('upload_excel')
            except Exception as e:
                messages.error(request, f"Erreur inattendue: {e}")
                return redirect('upload_excel')
        except Exception as e:
            messages.error(request, f"Erreur fichier Excel: {e}")
            return redirect('upload_excel')

    return render(request, 'Reporting/upload_excel.html', {'form': form})


    #IMPORTATION DE LA BALANCE OPTION 2

# from datetime import datetime
# import pytz
# import pandas as pd
# from django.shortcuts import render, redirect
# from django.contrib import messages
# import requests

# def upload_excel(request):
#     token = request.session.get("token")
#     form = UploadExcelForm()
#     if not token:
#         return redirect('login')

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {token}"
#     }

#     if request.method == 'POST':
#         excel_file = request.FILES['excel_file']
#         try:
#             # Charger le fichier avec openpyxl pour lire C2 (date)
#             wb = openpyxl.load_workbook(excel_file, data_only=True)
#             sheet = wb.active

#             # Récupérer la date dans C2 (cellule row=2, column=3)
#             raw_date = str(sheet.cell(row=2, column=3).value).strip().replace('.', '')
#             try:
#                 date_arrete = datetime.strptime(raw_date, "%d/%m/%Y")
#                 date_arrete_formatted = date_arrete.strftime("%-d/%-m/%Y")  # pour Linux/mac
#                 # Utilise ceci à la place si tu es sur Windows :
#                 # date_arrete_formatted = date_arrete.strftime("%#d/%#m/%Y")
#             except ValueError:
#                 raise ValueError(f"Format de date non valide dans la cellule C2 : {raw_date}")

#             # Lire les données à partir de la ligne 4 (header=3)
#             dataFile = pd.read_excel(excel_file, header=3)
#             items_data = []

#             for index, row in dataFile.iterrows():
#                 try:
#                     item = {
#                         "chapitre": str(row.get('Chapitre', '')),
#                         "intituleChapitre": str(row.get('Intitulé chapitre', None)),
#                         "codeDevise": str(row.get('Devise', 'XOF')),
#                         "numCompte": str(row['Numéro de Compte']),
#                         "intituleCompte": str(row.get('Intitulé du compte', None)),
#                         "numeroClient": str(row.get('Numéro Client', None)),
#                         "nomClient": str(row.get('Nom Client', None)),
#                         "soldeDebit": float(row.get('Solde débit DEVISE', 0.0) if pd.notna(row.get('Solde débit DEVISE')) else 0.0),
#                         "soldeCredit": float(row.get('Solde crédit DEVISE', 0.0) if pd.notna(row.get('Solde crédit DEVISE')) else 0.0),
#                         "soldeNet": float(row.get('soldeNet', 0.0) if pd.notna(row.get('soldeNet')) else 0.0),
#                         "resident": str(row.get('Résident (R / NR)', 'RESIDENT')).upper(),
#                         "codeAgentEconomique": str(row['Agent économique']),
#                         "codeSecteurActivite": str(row.get("Secteur d'activité", None)),
#                     }
#                     items_data.append(item)
#                 except KeyError as e:
#                     messages.error(request, f"Erreur: Colonne '{e}' manquante dans le fichier Excel à la ligne {index + 2}.")
#                     return render(request, 'Reporting/upload_excel.html', {'form': form})
#                 except Exception as e:
#                     messages.error(request, f"Erreur lors du traitement de la ligne {index + 2}: {e}")
#                     return render(request, 'Reporting/upload_excel.html', {'form': form})

#             transmission_data = {
#                 "dateArrete": date_arrete_formatted,
#                 "statut": "CREATION"
#             }

#             payload = {
#                 "transmission": transmission_data,
#                 "versionAPI": "1.0.0",
#                 "items": items_data,
#                 "items2": []
#             }

#             api_url = "https://syrif.bcrg-guinee.org:8186/api/balance"
#             try:
#                 response = requests.post(api_url, json=payload, headers=headers)
#                 response.raise_for_status()
#                 print(response.json())
#                 msg = f"Erreur Données invalide ou incomplète {response.json().get('description')}"
#                 messages.error(request, msg)
#                 return redirect('upload_excel')
#             except requests.exceptions.RequestException as e:
#                 messages.error(request, f"Erreur lors de l'envoi des données à l'API: {e}")
#                 return render(request, 'Reporting/upload_excel.html')
#             except Exception as e:
#                 messages.error(request, f"Erreur inattendue: {e}")
#                 return render(request, 'Reporting/upload_excel.html')
#         except FileNotFoundError:
#             messages.error(request, "Erreur: Le fichier Excel n'a pas été trouvé.")
#         except Exception as e:
#             messages.error(request, f"Erreur lors de la lecture du fichier Excel: {e}")

#     return render(request, 'Reporting/upload_excel.html')




def upload_success(request):
    return render(request, 'Reporting/upload_success.html')

# modification du mot de passe utilisateur
import requests
from django.shortcuts import render, redirect
from django.contrib import messages

def modifyPassword(request):
    token = request.session.get("token")
    print(token)
    if not token:
        return redirect('login')

    if request.method == 'POST':
        password = request.POST.get('password')
        passwordConfirm = request.POST.get('passwordConfirm')

        if password != passwordConfirm:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, 'Reporting/ModifyPassword.html') # Rendre le formulaire à nouveau avec l'erreur

        data = {
            "token": token,
            "password": password,
            "confirmPassword": passwordConfirm
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(
                "https://syrif.bcrg-guinee.org:8186/util/rpwd",
                headers=headers,
                json=data
            )
            response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP

            print(response.json())
            if response.status_code == 200:
                messages.success(request, "Modification de mot de passe effectuée avec succès")
                return redirect('home') # Retourner la redirection après succès
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', "Impossible de modifier le mot de passe. Veuillez réessayer.")
                except ValueError: # Si la réponse n'est pas du JSON
                    error_message = f"Impossible de modifier le mot de passe. Statut: {response.status_code}"
                messages.error(request, error_message)
                return render(request, 'Reporting/ModifyPassword.html', {'error_details': error_message}) # Afficher l'erreur et rendre le formulaire

        except requests.exceptions.RequestException as e:
            messages.error(request, f"Erreur de connexion: vérifiez votre connexion internet. Détails: {e}")
            return render(request, 'Reporting/ModifyPassword.html') # Rendre le formulaire avec l'erreur de connexion

    return render(request, 'Reporting/ModifyPassword.html') # Afficher le formulaire initialement

# recuperation du mot de passe utilisateur
#vue pour juste vérifier l'existance de l'utisateur et de recupérer le reset token
def userResetToken(request):
    if request.method == "POST":
        username = request.POST.get('username')
        headers = {
            "Content-Type": "application/json",
            
        }
        data = {
            "username":username
        }

    


        try:
            response = requests.post(
                "https://syrif.bcrg-guinee.org:8186/util/fpwd",
                headers=headers,
                json=data
            )
            # response.raise_for_status()
            if response.status_code == 200:
                reset_token = response.json().get('resetToken') 
                request.session['resetToken'] = reset_token 
                # Envoie de Mail pour la récupération de mot de passe 
                subject = "Recuperation de mot depasse"
                message = f"Cliquez sur ce lien pour réinitialiser votre mot de passe http://127.0.0.1:8000/auth/password/resetpwd/"
                from_email = settings.EMAIL_HOST_USER
                to_email = username
                email = EmailMessage(subject,message,from_email,[to_email])
                email.send()
                messages.success(request," Un lien vient d'être envoyé dans votre boîte mail veillez consulter. MERCI !")
                return redirect('resetUser')
            else:
                # Gérer les erreurs de connexion
                if response.status_code == 404:
                    error = "Compte non trouvé, veuillez réessayer !"
                    messages.error(request,error)
                elif response.status_code == 403:
                    error =  "Accès interdit."
                    messages.error(request,error)
                else:
                   error = "Informations incorrectes. veuillez réessayer."
                   messages.error(request,error)
                return redirect('resetUser')

            
        except requests.exceptions.RequestException as e:
            messages.error(request, "Erreur de connexion: vérifiez votre connexion internet !")
            return redirect('resetUser') # Rendre le formulaire avec l'erreur de connexion
   
    return render(request,"Reporting/ResetPassword.html")

#vue qui permet la réinitialisation du mot de passe
def resetPwd(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        passwordConfirm = request.POST.get('passwordConfirm')

        if not all([password,passwordConfirm]):
            messages.error(request,"Les champs sont obligatoires ")
            return redirect('resetPwd')

        if password != passwordConfirm:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, 'Reporting/ModifyPassword.html') # Rendre le formulaire à nouveau avec l'erreur
        
        if len(password) < 6:
            messages.error(request, "Le mot de passe doit contenir au moins 6 caractères.")
            return redirect('resetPwd')
        elif not re.search(r'[A-Za-z]', password):
            messages.error(request, "Le mot de passe doit contenir au moins une lettre.")
            return redirect('resetPwd')
        elif not re.search(r'\d', password):
            messages.error(request, "Le mot de passe doit contenir au moins un chiffre.")
            return redirect('resetPwd')
        elif not re.search(r'[!@#$%^&*()_+=\-{}\[\]:;"\'<>,.?/\\|`~]', password):
            messages.error(request, "Le mot de passe doit contenir au moins un caractère spécial.")
            return redirect('resetPwd')
        if password != passwordConfirm:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, 'Reporting/ModifyPassword.html')


        reset_token=request.session.get("resetToken")
        data = {
            "token": reset_token,
            "password": password,
            "confirmPassword": passwordConfirm
        }

        headers = {
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                "https://syrif.bcrg-guinee.org:8186/util/rpwd",
                headers=headers,
                json=data
            )
            response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP

            if response.status_code == 200:
                messages.success(request, "Modification de mot de passe effectuée avec succès, veuillez vous reconnecter ! ")
                return redirect('login') # Retourner la redirection après succès
            else:
                
                messages.error(request, "Impossible de réinitialiser le mot de passe ! ")
                return redirect('resetPwd') # Afficher l'erreur et rendre le formulaire

        except requests.exceptions.RequestException as e:
            messages.error(request, "Erreur de connexion: vérifiez votre connexion internet !")
            return render(request, 'Reporting/ModifyPassword.html') # Rendre le formulaire avec l'erreur de connexion


    return render(request,'Reporting/ModifyPassword.html')


