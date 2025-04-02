from firebase_admin import firestore, credentials, initialize_app, storage
from flask import request, jsonify, session, current_app, Flask, render_template, redirect, url_for, flash
import firebase_admin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import logging
import re
import uuid
import os
import string
import random
import datetime
import secrets
import json
from collections import OrderedDict
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_session import Session
from datetime import timedelta, datetime

app = Flask(__name__)
app.secret_key = os.urandom(48).hex()

app.config['UPLOAD_FOLDER'] = 'temp_uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

UPLOAD_FOLDER = 'static/uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Wczytanie bazy danych
cred = credentials.Certificate(
    "multi-fach-firebase-adminsdk-fbsvc-6a21166fa1.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'multi-fach.appspot.com'
})
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()
bucket = storage.bucket()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "nazwiskotestoweimietestowe@gmail.com"
EMAIL_PASSWORD = "kpyf ytqo izms etbc"

verification_tokens = {}


@app.route("/send_email", methods=["POST"])
def send_email():
    try:
        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"].strip()
        # Pobranie własnego tematu (jeśli istnieje)
        custom_subject = request.form.get("custom_subject", "").strip()
        message = request.form["message"]

        # Obsługa "Inne zapytanie"
        if subject == "Inne zapytanie" and custom_subject:
            # Łączymy temat z własnym zapytaniem
            subject = f"Inne zapytanie - {custom_subject}"
        elif not subject:  # Jeśli temat jest pusty (dla bezpieczeństwa)
            subject = "Zapytanie ze strony"

        # Tworzenie wiadomości e-mail
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = "mariamarysia1212@gmail.com"
        msg["Subject"] = f"Nowa wiadomość od {name}: {subject}"
        body = f"Od: {name} ({email})\n\nTreść wiadomości:\n{message}"
        msg.attach(MIMEText(body, "plain"))

        # Połączenie z serwerem SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(
            EMAIL_SENDER, "mariamarysia1212@gmail.com", msg.as_string())
        server.quit()

        flash("E-mail został wysłany!", "success")
    except Exception as e:
        flash(f"Błąd wysyłki: {e}", "danger")

    return redirect(url_for('kontakt'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/add_announcement', methods=['POST'])
def add_announcement():
    if "user" not in session:
        return jsonify({"success": False, "error": "Brak autoryzacji"}), 403

    try:
        # Pobieranie danych z formularza
        collection_name = request.form.get('type', '').strip()
        doc_name = request.form.get('category', '').strip()
        field_name = request.form.get('field_name', '').strip()
        item_name = request.form.get('item_name', '').strip()
        new_doc_name = request.form.get('new_doc_name', '').strip()

        # Obsługa „Inne” dla kategorii
        if doc_name == "other" and new_doc_name:
            doc_name = new_doc_name.strip()
        if not doc_name or not field_name:
            return jsonify({"success": False, "error": "Nieprawidłowe dane wejściowe"}), 400

        # Generowanie unikalnej nazwy dla `item_name`
        if not item_name:
            item_name = f"ogłoszenie_{uuid.uuid4().hex[:8]}"

        item_name = re.sub(r'[^a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ-]', ' ', item_name)
        field_name = re.sub(
            r'[^a-zA-Z0-9_ąęćłńóśźżĄĘĆŁŃÓŚŹŻ-]', '_', field_name)

        # Pobieranie i konwersja danych liczbowych
        def parse_int(value, default=0):
            try:
                return int(value)
            except ValueError:
                return default

        deposit = parse_int(request.form.get('deposit', '0'))
        min_hours = parse_int(request.form.get('min_hours', '1'))
        hour_to_day = parse_int(request.form.get('hour_to_day', '1'))
        available = parse_int(request.form.get('available', '1'))
        hidden = parse_int(request.form.get('hidden', '0'))
        price_hour = parse_int(request.form.get('price_hour', '0'))
        price_day = parse_int(request.form.get('price_day', '0'))
        transport = parse_int(request.form.get('transport', '0'))
        piece = parse_int(request.form.get('piece', '1'))

        # Obsługa parametrów
        raw_parameters = request.form.get('parameters', '').strip()
        parameters_dict = {
            key.strip(): value.strip()
            for line in raw_parameters.split("\n") if ":" in line
            for key, value in [line.split(":", 1)]
        }

        # Obsługa zdjęcia (lokalne przechowywanie)
        image_url = "../static/img/multi-fach_sklep.jpg"  # Domyślne zdjęcie
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(filepath)  # Zapis pliku lokalnie
                # Ścieżka do obrazu w serwerze Flask
                image_url = f"/{filepath}"

        # Tworzenie danych dla ogłoszenia
        announcement_data = {
            "item_name": item_name,
            "desc": request.form.get('desc', '').strip(),
            "deposit": deposit,
            "min_hours": min_hours,
            "hour_to_day": hour_to_day,
            "available": available,
            "hidden": hidden,
            "price_hour": price_hour,
            "price_day": price_day,
            "producent": request.form.get('producent', '').strip(),
            "transport": transport,
            "parameters": parameters_dict,
            "piece": piece,
            "image": image_url,
            "added_by": session.get("user"),
            "created_at": datetime.datetime.utcnow()
        }

        # Sprawdzenie, czy dokument już istnieje
        doc_ref = db.collection(collection_name).document(doc_name)
        doc = doc_ref.get()

        if doc.exists:
            doc_data = doc.to_dict()
            if field_name in doc_data:
                return jsonify({"success": False, "error": f"Pole '{field_name}' już istnieje."}), 400
            else:
                doc_ref.update({field_name: announcement_data})
        else:
            doc_ref.set({field_name: announcement_data})

        return jsonify({"success": True, "message": "Ogłoszenie dodane pomyślnie"}), 201

    except Exception as e:
        logging.error(f"Błąd dodawania ogłoszenia: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def get_user_data(email):
    try:
        if not email:
            logging.warning("Adres e-mail jest pusty!")
            return {}

        email = email.lower().strip()
        user_ref = db.collection("admin").document(email)
        user = user_ref.get()

        if user.exists:
            return user.to_dict()
        else:
            logging.warning(f"⚠ Użytkownik {email} nie istnieje w bazie.")
            return {}  # Możesz zwrócić `{}` zamiast `None`, aby uniknąć błędów przy dalszym używaniu

    except Exception as e:
        logging.error(
            f"Błąd podczas pobierania użytkownika {email}: {str(e)}")
        return {}


# Funkcja generowania kodu PIN i tokena
def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Funkcja wysyłania kodu weryfikacyjnego (tokena) na e-mail


def send_verification_token(email, token):
    # Nadpisanie adresu e-mail na stały adres docelowy
    email = "nazwiskotestoweimietestowe@gmail.com"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = email
    msg["Subject"] = "Twój kod weryfikacyjny (token)"

    body = f"Twój kod weryfikacyjny: {token}\n\nNie udostępniaj go nikomu."
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
        print(f"E-mail z tokenem wysłany na {email}")
    except Exception as e:
        print(f"Błąd podczas wysyłania e-maila: {e}")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("index.html")

    email = request.form.get('email')
    login = request.form.get('login')
    password = request.form.get('password')
    code = request.form.get('code')

    if not email or not login or not password or not code:
        flash("Podaj wszystkie wymagane dane!", "warning")
        return redirect(url_for('index'))

    user_ref = db.collection("admin").document(email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("Nie znaleziono użytkownika!", "danger")
        return redirect(url_for('index'))

    user = user_doc.to_dict()

    if user.get("is_banned", False):
        flash(
            "Twoje konto zostało zablokowane po 3 nieudanych próbach logowania.", "danger")
        return redirect(url_for('index'))

    stored_login = user.get('login')
    stored_code = user.get('code')
    stored_password = user.get('password')

    login_valid = check_password_hash(stored_login, login)
    code_valid = check_password_hash(stored_code, code)
    password_valid = check_password_hash(stored_password, password)

    if not (login_valid and code_valid and password_valid):
        session[f'failed_attempts_{email}'] = session.get(
            f'failed_attempts_{email}', 0) + 1

        if session[f'failed_attempts_{email}'] >= 3:
            user_ref.update({"is_banned": True})
            send_ban_notification(email)
            flash(
                "Twoje konto zostało zablokowane po 3 nieudanych próbach logowania.", "danger")
            return redirect(url_for('index'))

        flash(
            f"Niepoprawne dane logowania! Pozostałe próby: {3 - session[f'failed_attempts_{email}']}", "danger")
        return redirect(url_for('index'))

    existing_session_id = user.get("session_id")
    if existing_session_id:
        flash("Twoje konto jest już zalogowane na innym urządzeniu.", "danger")
        return redirect(url_for('index'))

    session.pop(f'failed_attempts_{email}', None)
    session_id = str(uuid.uuid4())
    generated_token = generate_code()
    session['verification_token'] = generated_token
    session['verification_email'] = email
    session['pending_session_id'] = session_id
    session['token_timestamp'] = datetime.utcnow().isoformat()
    session['last_activity'] = datetime.utcnow().isoformat()

    send_verification_token(email, generated_token)
    flash("Kod weryfikacyjny (token) został wysłany na Twój e-mail.", "info")
    return redirect(url_for('verify'))


@app.before_request
def check_session_timeout():
    if 'user' in session and request.endpoint not in ('static', 'favicon.ico'):
        last_activity = session.get('last_activity')
        if last_activity:
            try:
                last_activity_time = datetime.fromisoformat(last_activity)
                if (datetime.utcnow() - last_activity_time).total_seconds() > 600:
                    email = session.get("user")
                    session.clear()
                    db.collection("admin").document(
                        email).update({"session_id": None})
                    flash("Zostałeś wylogowany z powodu braku aktywności.", "warning")
                    return redirect(url_for('index'))
            except ValueError:
                session.clear()
                flash("Błąd sesji. Zostałeś wylogowany.", "danger")
                return redirect(url_for('index'))
        session['last_activity'] = datetime.utcnow().isoformat()


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    email = session.get('verification_email')
    if not email:
        flash("Brak adresu e-mail. Spróbuj ponownie.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        entered_token = request.form.get('token')
        stored_token = session.get('verification_token')
        token_timestamp = session.get('token_timestamp')

        if not stored_token or not token_timestamp:
            flash("Brak ważnego tokenu. Spróbuj ponownie.", "danger")
            return redirect(url_for('index'))

        try:
            token_time = datetime.fromisoformat(token_timestamp)
            current_time = datetime.utcnow()
        except ValueError:
            session.pop('verification_token', None)
            session.pop('token_timestamp', None)
            flash("Błąd w odczycie tokenu. Poproś o nowy kod weryfikacyjny.", "danger")
            return redirect(url_for('login'))

        if (current_time - token_time).total_seconds() > 180:
            session.pop('verification_token', None)
            session.pop('token_timestamp', None)
            flash("Token wygasł. Poproś o nowy kod weryfikacyjny.", "danger")
            return redirect(url_for('login'))

        if entered_token.strip() == stored_token:
            session_id = session.pop('pending_session_id', None)
            session['user'] = email
            session['session_id'] = session_id
            session['last_activity'] = datetime.utcnow().isoformat()
            db.collection("admin").document(
                email).update({"session_id": session_id})
            session.pop('verification_token', None)
            session.pop('verification_email', None)
            session.pop('token_timestamp', None)
            flash("Zalogowano pomyślnie!", "success")
            return redirect(url_for('admin_panel'))
        else:
            flash("Niepoprawny kod weryfikacyjny. Spróbuj ponownie.", "danger")
            return redirect(url_for('verify'))

    return render_template("verify_token.html", email=email)


@app.before_request
def check_active_session():
    if "user" in session:
        email = session["user"]
        session_id = session.get("session_id")

        user_ref = db.collection("admin").document(email)
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            if user_data.get("session_id") != session_id:
                session.clear()
                flash(
                    "Zostałeś wylogowany, ponieważ ktoś zalogował się na Twoje konto.", "warning")
                return redirect(url_for("index"))


@app.route('/logout')
def logout():
    if "user" in session:
        email = session["user"]
        db.collection("admin").document(email).update(
            {"session_id": None})  # Usunięcie session_id
    session.clear()
    flash("Zostałeś wylogowany.", "info")
    return redirect(url_for('index'))

# PAMIĘTAJ O USUNIĘCIU OSTATNIEGO / Z LINKA!!!


def send_ban_notification(email):
    try:
        # Generowanie unikalnego tokena (np. 32-znakowy)
        unban_token = secrets.token_urlsafe(32)

        # Zapisanie tokena w Firestore (zastępuje poprzedni, jeśli istniał)
        db.collection("admin").document(email).update(
            {"unban_token": unban_token})

        # Tworzenie unikalnego linku do odbanowania
        unban_link = f"http://localhost:5000/unban?email={email}&token={unban_token}"

        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_SENDER  # email
        msg["Subject"] = "Twoje konto zostało zablokowane"

        body = f"""
        Witaj,

        Twoje konto zostało zablokowane po 3 nieudanych próbach logowania.
        Jeśli uważasz, że to pomyłka, kliknij poniższy link, aby odbanować swoje konto:

        {unban_link}u

        UWAGA: Ten link jest jednorazowy i wygasa po użyciu.

        Jeśli to nie Ty próbowałeś się logować, skontaktuj się z administratorem.

        Pozdrawiamy,
        Zespół Wsparcia
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_SENDER, msg.as_string())

        print(
            f" E-mail z informacją o banie i linkiem do odbanowania wysłany do {email}")

    except Exception as e:
        print(f" Błąd podczas wysyłania e-maila o banie: {str(e)}")


@app.route('/unban', methods=['GET'])
def unban_user():
    email = request.args.get('email')
    token = request.args.get('token')

    if not email or not token:
        flash("Nieprawidłowe żądanie odbanowania.", "danger")
        return redirect(url_for('index'))

    try:
        # Pobieramy użytkownika z Firestore
        user_ref = db.collection("admin").document(email)
        user_data = user_ref.get()

        if not user_data.exists:
            flash("Nie znaleziono użytkownika.", "danger")
            return redirect(url_for('index'))

        user_data = user_data.to_dict()
        stored_token = user_data.get("unban_token")

        # Sprawdzamy, czy token się zgadza i istnieje
        if not stored_token or stored_token != token:
            flash("Nieprawidłowy lub wygasły token odbanowania.", "danger")
            return redirect(url_for('index'))

        #  Resetujemy licznik prób logowania po odbanowaniu
        session.pop(f'failed_attempts_{email}', None)

        #  Aktualizujemy Firestore: usuwamy token i odblokowujemy użytkownika
        user_ref.update({"is_banned": False, "unban_token": None})

        flash("Konto zostało pomyślnie odbanowane. Masz ponownie 3 próby logowania.", "success")
        print(f" Konto {email} zostało odbanowane, licznik prób zresetowany!")

    except Exception as e:
        flash("Wystąpił błąd podczas odbanowywania konta.", "danger")
        print(f" Błąd podczas odbanowywania użytkownika {email}: {str(e)}")

    return redirect(url_for('index'))


# @app.route('/register', methods=['POST'])
# def register():
#     email = request.form.get('email')
#     login = request.form.get('login')
#     code = request.form.get('code')
#     password = request.form.get('password')

#     if not email or not login or not code or not password:
#         return redirect(url_for('index'))

#     user_ref = db.collection("admin").document(email)
#     user = user_ref.get()

#     if user.exists:
#         return redirect(url_for('index'))

#     hashed_login = generate_password_hash(login)
#     hashed_code = generate_password_hash(code)
#     hashed_password = generate_password_hash(password)

#     user_data = {
#         "login": hashed_login,
#         "code": hashed_code,
#         "password": hashed_password
#     }

#     user_ref.set(user_data)

#     flash("Rejestracja zakończona sukcesem!", "success")
#     return redirect(url_for('admin_panel'))


def get_collection_data(collection_name):
    try:
        docs = db.collection(collection_name).stream()
        collection_list = []

        for doc in docs:
            doc_data = doc.to_dict()
            doc_data["id"] = doc.id
            collection_list.append(doc_data)

        return jsonify(collection_list), 200
    except Exception as e:
        print(f"Błąd pobierania danych z kolekcji {collection_name}: {e}")
        return jsonify({"error": str(e)}), 500

# Dynamiczne pobieranie danych dla każdej kolekcji


@app.route('/<collection>_get', methods=['GET'])
def get_collection(collection):
    if collection not in ["renthings", "services", "products"]:
        return jsonify({"error": "Nieprawidłowa kolekcja"}), 400
    return get_collection_data(collection)


@app.route('/details/<collection>/<doc_id>/<item_name>')
def details_page(collection, doc_id, item_name):
    doc_ref = db.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Dokument '{doc_id}' w kolekcji '{collection}' nie istnieje", 404

    doc_data = doc.to_dict()
    item_data = doc_data.get(item_name, {})

    return render_template(
        "details.html",
        collection=collection,
        doc_id=doc_id,
        item_name=item_name,
        data=item_data,
    )


@app.route('/edit_details/<collection>/<doc_id>/<item_name>', methods=['GET'])
def edit_details_page(collection, doc_id, item_name):
    if "user" not in session:
        flash("Musisz być zalogowany, aby uzyskać dostęp do edycji.", "warning")
        return redirect(url_for("index"))

    doc_ref = db.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Błąd: Dokument '{doc_id}' w kolekcji '{collection}' nie istnieje.", 404

    doc_data = doc.to_dict() or {}
    single_ad_data = doc_data.get(item_name, {})

    if not isinstance(single_ad_data, dict):
        flash("Błąd: Dane ogłoszenia są niepoprawne.", "danger")
        return redirect(url_for("index"))

    # Pobranie listy dokumentów dla kolekcji
    doc_list = get_all_document_names_from_collection(collection)

    # Upewnienie się, że parameters to słownik
    parameters = single_ad_data.get("parameters", {})
    if isinstance(parameters, str):
        try:
            parameters = eval(parameters)
        except:
            parameters = {}

    image_path = single_ad_data.get("image", "/static/img/default.jpg")

    return render_template(
        "edit_details.html",
        collection=collection,
        doc_id=doc_id,
        item_name=item_name,
        image=image_path,
        hidden=single_ad_data.get("hidden", ""),
        price_day=single_ad_data.get("price_day", "0"),
        price_hour=single_ad_data.get("price_hour", "0"),
        hour_to_day=single_ad_data.get("hour_to_day", "24"),
        min_hours=single_ad_data.get("min_hours", "1"),
        piece=single_ad_data.get("piece", "1"),
        transport=single_ad_data.get("transport", "0"),
        deposit=single_ad_data.get("deposit", "0"),
        available=single_ad_data.get("available", "1"),
        parameters=parameters,
        desc=single_ad_data.get("desc", ""),
        producent=single_ad_data.get("producent", ""),
        doc_list=doc_list
    )


def map_to_text(parameters):
    if isinstance(parameters, dict):
        return "\n".join(f"{key}: {value}" for key, value in parameters.items())
    return ""


app.jinja_env.filters['map_to_text'] = map_to_text


def get_all_document_names_from_collection(collection):
    try:
        docs = db.collection(collection).stream()
        doc_list = [doc.id for doc in docs]
        doc_list.append("other")  # Dodanie opcji "Inna" na końcu
        return doc_list
    except Exception as e:
        logging.error(
            f"Błąd podczas pobierania dokumentów z kolekcji '{collection}': {str(e)}")
        return []


@app.route('/edit_details/<collection>/<doc_id>/<item_name>', methods=['POST'])
def update_details(collection, doc_id, item_name):
    if "user" not in session:
        flash("Musisz być zalogowany, aby uzyskać dostęp do edycji.", "warning")
        return redirect(url_for("login"))

    doc_ref = db.collection(collection).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        flash(
            f"Dokument '{doc_id}' w kolekcji '{collection}' nie istnieje.", "danger")
        return redirect(url_for("index"))

    doc_data = doc.to_dict() or {}
    single_ad_data = doc_data.get(item_name, {})

    if not isinstance(single_ad_data, dict):
        flash("Błąd: Dane ogłoszenia są niepoprawne.", "danger")
        return redirect(url_for("index"))

    updated_data = {key: request.form.get(key) for key in request.form.keys()}

    fields_to_update = [
        "item_name", "producent", "desc", "price_day", "price_hour",
        "hour_to_day", "deposit", "available", "transport", "piece", "min_hours"
    ]

    hidden_value = request.form.get("hidden", "0")
    single_ad_data["hidden"] = "1" if hidden_value == "1" else "0"

    for field in fields_to_update:
        if field in updated_data and updated_data[field] is not None:
            try:
                single_ad_data[field] = int(updated_data[field]) if field in [
                    "price_day", "price_hour", "deposit", "available", "transport", "piece", "min_hours", "hour_to_day"] else updated_data[field]
            except ValueError:
                flash(
                    f"Błąd: Nieprawidłowa wartość dla pola {field}.", "danger")
                return redirect(url_for("edit_details_page", collection=collection, doc_id=doc_id, item_name=item_name))

    new_collection = request.form.get("new_collection", collection)
    new_doc_id = request.form.get("new_doc_id", doc_id)
    new_field_name = request.form.get("new_field_name", item_name)

    if new_collection != collection or new_doc_id != doc_id or new_field_name != item_name:
        new_doc_ref = db.collection(new_collection).document(new_doc_id)
        new_doc_data = new_doc_ref.get().to_dict() or {}
        new_doc_data[new_field_name] = single_ad_data
        new_doc_ref.set(new_doc_data, merge=True)
        doc_ref.update({item_name: firestore.DELETE_FIELD})
        flash("Ogłoszenie zostało przeniesione i zaktualizowane.", "success")
        return redirect(url_for('edit_details_page', collection=new_collection, doc_id=new_doc_id, item_name=new_field_name))

    if 'image' in request.files and request.files['image'].filename:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(
                current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            single_ad_data["image"] = f"/static/uploads/{unique_filename}"

    raw_parameters = request.form.get('parameters', '').strip()
    if raw_parameters:
        parameters_dict = {
            key.strip(): value.strip()
            for line in raw_parameters.split("\n") if ":" in line
            for key, value in [line.split(":", 1)]
        }
        single_ad_data["parameters"] = parameters_dict

    try:
        doc_ref.update({item_name: single_ad_data})
        flash("Ogłoszenie zostało zaktualizowane.", "success")
    except Exception as e:
        flash(f"Wystąpił błąd podczas aktualizacji: {str(e)}", "danger")

    return redirect(url_for('edit_details_page', collection=collection, doc_id=doc_id, item_name=item_name))


@app.route('/delete_announcement/<collection>/<doc_id>/<item_name>', methods=['POST'])
def delete_announcement(collection, doc_id, item_name):
    if "user" not in session:
        flash("Musisz być zalogowany, aby usunąć ogłoszenie.", "warning")
        return redirect(url_for("index"))

    doc_ref = db.collection(collection).document(doc_id)
    try:
        doc_ref.update({item_name: firestore.DELETE_FIELD})
        flash("Ogłoszenie zostało usunięte.", "success")
    except Exception as e:
        flash(f"Błąd podczas usuwania: {str(e)}", "danger")

    return redirect(url_for('edit_announcements'))


@app.route("/")
@app.route("/index")
def index():
    try:
        # Pobranie dokumentu "main" z Firestore
        doc_main_ref = db.collection("content").document("main")
        doc_main = doc_main_ref.get()
        main_data = doc_main.to_dict() if doc_main.exists else {}

        # Pobranie treści strony głównej
        main_content = main_data.get("main_side_content", "Brak treści")

        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()
        pon_pt = doc_info.to_dict().get(
            "pon_pt", "Brak danych") if doc_info.exists else "Brak danych"
        so = doc_info.to_dict().get("so", "Brak danych") if doc_info.exists else "Brak danych"

        # Pobranie stopki
        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        main_content = "Błąd ładowania treści"
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    return render_template("index.html", main_content=main_content, pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/uslugi")
def uslugi():
    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("uslugi.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/kontakt")
def kontakt():
    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("kontakt.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/sklep")
def sklep():
    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("sklep.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/wypozyczalnia")
def wypozyczalnia():
    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("wypozyczalnia.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/admin")
def admin():
    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("admin.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/verify_token")
def verify_token():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))
    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    return render_template("verify_token.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/admin_panel")
def admin_panel():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))

    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("admin_panel.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/edit_announcements")
def edit_announcements():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))

    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("edit_announcements.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/edit_main_side")
def edit_main_side():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))

    try:
        # Pobranie treści strony głównej (main_side_content) z Firestore
        doc_main_ref = db.collection("content").document("main")
        doc_main = doc_main_ref.get()
        main_content = doc_main.to_dict().get(
            "main_side_content", "Brak treści") if doc_main.exists else "Brak treści"

        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()
        pon_pt = doc_info.to_dict().get(
            "pon_pt", "Brak danych") if doc_info.exists else "Brak danych"
        so = doc_info.to_dict().get("so", "Brak danych") if doc_info.exists else "Brak danych"

        # Pobranie stopki
        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        main_content = "Błąd ładowania treści"
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    return render_template("edit_main_side.html", main_content=main_content, pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/edit_info")
def edit_info():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))

    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("edit_info.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/edit_footer")
def edit_footer():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))

    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("edit_footer.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route("/add_announcements")
def add_announcements():
    if "user" not in session:
        flash(
            "Musisz być zalogowany, aby uzyskać dostęp do panelu administratora.", "warning")
        return redirect(url_for("index"))

    try:
        # Pobranie godzin otwarcia
        doc_info_ref = db.collection("content").document("info")
        doc_info = doc_info_ref.get()

        if doc_info.exists:
            pon_pt = doc_info.to_dict().get("pon_pt", "Brak danych")
            so = doc_info.to_dict().get("so", "Brak danych")
        else:
            pon_pt = "Brak danych"
            so = "Brak danych"

        doc_footer_ref = db.collection("content").document("footer")
        doc_footer = doc_footer_ref.get()
        footer_content = doc_footer.to_dict().get(
            "main_content", "Treść stopki") if doc_footer.exists else "Treść stopki"

    except Exception as e:
        print("Błąd pobierania danych z Firestore:", e)
        pon_pt = "Błąd"
        so = "Błąd"
        footer_content = "Błąd ładowania stopki"

    # Przekazujemy dane do szablonu 'uslugi.html'
    return render_template("add_announcements.html", pon_pt=pon_pt, so=so, footer_content=footer_content)


@app.route('/get_document_names')
def get_document_names():
    collection = request.args.get('collection', '').strip()

    # Jeśli nie podano kolekcji → zwracamy wszystkie dokumenty
    if not collection:
        all_docs = []
        for coll in db.collections():
            docs = [doc.id for doc in coll.stream()]
            all_docs.extend(docs)
        return jsonify(list(set(all_docs)))

    # Pobieramy tylko dokumenty z podanej kolekcji
    try:
        docs = [doc.id for doc in db.collection(collection).stream()]
        return jsonify(docs)
    except Exception as e:
        print(" Błąd pobierania dokumentów:", str(e))
        return jsonify([]), 500


@app.errorhandler(404)
def page_not_found(error):
    logging.warning(f"Nie znaleziono strony: {request.url} - Błąd: {error}")
    return render_template("404.html"), 404


@app.route('/get_subjects')
def get_subjects():
    try:
        doc_ref = db.collection('content').document('contact')
        doc = doc_ref.get()
        if doc.exists:
            subjects = doc.to_dict().get('subjects', [])  # Pobieramy tablicę
            return jsonify(subjects)
        else:
            # Jeśli dokument nie istnieje, zwracamy pustą listę
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_hours', methods=['POST'])
def update_hours():
    pon_pt = request.form.get("pon_pt")
    so = request.form.get("so")

    doc_ref = db.collection("content").document("info")

    try:
        # Aktualizacja dokumentu w Firestore
        doc_ref.update({
            "pon_pt": pon_pt,
            "so": so
        })
        return redirect(url_for('edit_info'))
    except Exception as e:
        return f"Błąd aktualizacji: {e}", 500


@app.route("/update_main", methods=["POST"])
def update_main():
    try:
        main_side_content = request.form.get("main_side_content")
        doc_ref = db.collection("content").document("main")
        doc_ref.update({"main_side_content": main_side_content})
        return redirect(url_for("edit_main_side"))
    except Exception:
        return "Błąd podczas aktualizacji strony głównej", 500


@app.route("/update_footer", methods=["POST"])
def update_footer():
    try:
        footer_content = request.form.get("footer_content")
        doc_ref = db.collection("content").document("footer")
        doc_ref.update({"main_content": footer_content})
        return redirect(url_for("edit_footer"))
    except Exception:
        return "Błąd podczas aktualizacji stopki", 500


if __name__ == '__main__':
    app.run(debug=True)
