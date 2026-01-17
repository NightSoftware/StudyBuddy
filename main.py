import json
import os
import uuid
import hashlib
import logging
import shutil
import getpass
from pathlib import Path
from datetime import datetime, date, timedelta

# ================= CONFIG =================
DATA = Path("data")
FILES = {
    "users": DATA / "users.json",
    "decks": DATA / "decks.json",
    "cards": DATA / "cards.json",
    "srs": DATA / "srs_state.json",
    "reviews": DATA / "reviews.json",
}

logging.basicConfig(
    filename="studybuddy.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


# ================= STORAGE =================
def init_storage():
    """Veri klasörünü ve dosyalarını hazırlar."""
    DATA.mkdir(exist_ok=True)
    for f in FILES.values():
        if not f.exists():
            atomic_write(f, [])


def read(path):
    """JSON dosyasını okur."""
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content) if content else []
    except:
        return []


def atomic_write(path, data):
    """Güvenli dosya yazma işlemi (Atomic Write)."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


# ================= AUTH =================
def hash_pwd(pwd, salt=None):
    """Parolayı hashler ve salt ile döner."""
    salt = salt or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt, 100_000)
    return h.hex(), salt.hex()


def register(email=None, pwd=None):
    if email is None:
        email = input("Email: ").strip()
    if pwd is None:
        pwd = getpass.getpass("Password: ").strip()

    users = read(FILES["users"])
    for u in users:
        if u["email"] == email:
            raise ValueError("Bu email zaten kayıtlı")

    h, s = hash_pwd(pwd)
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": h,
        "salt": s,
        "created_at": datetime.now().isoformat()
    }
    users.append(user)
    atomic_write(FILES["users"], users)
    logging.info(f"REGISTER SUCCESS: {email}")
    return user


def login(email=None, pwd=None):
    if email is None:
        email = input("Email: ").strip()
    if pwd is None:
        pwd = getpass.getpass("Password: ").strip()

    for u in read(FILES["users"]):
        if u["email"] == email:
            h, _ = hash_pwd(pwd, bytes.fromhex(u["salt"]))
            if h == u["password_hash"]:
                logging.info(f"LOGIN SUCCESS: {email}")
                return u
            raise ValueError("Hatalı parola")
    raise ValueError("Kullanıcı bulunamadı")


# ================= DECK =================
def list_decks(user):
    decks = [d for d in read(FILES["decks"]) if d["user_id"] == user["id"]]
    if not decks:
        print("Sistemde kayıtlı desteniz bulunmamaktadır.")
    for d in decks:
        print(f"ID: {d['id']} | Ad: {d['name']}")
    return decks


def create_deck(user, name=None):
    if name is None:
        name = input("Deste adı: ")
    decks = read(FILES["decks"])
    new_deck = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": name
    }
    decks.append(new_deck)
    atomic_write(FILES["decks"], decks)
    print("Deste oluşturuldu.")
    return new_deck


def delete_deck(user, did=None):
    if did is None:
        did = input("Silinecek Deste ID: ")

    decks = [d for d in read(FILES["decks"]) if not (d["id"] == did and d["user_id"] == user["id"])]
    cards_all = read(FILES["cards"])
    cards_to_keep = [c for c in cards_all if c["deck_id"] != did]
    removed_card_ids = {c["id"] for c in cards_all if c["deck_id"] == did}
    srs = [s for s in read(FILES["srs"]) if s["card_id"] not in removed_card_ids]

    atomic_write(FILES["decks"], decks)
    atomic_write(FILES["cards"], cards_to_keep)
    atomic_write(FILES["srs"], srs)
    print("Deste ve bağlı tüm kartlar silindi.")


# ================= CARD =================
def add_card(user, did=None, front=None, back=None):
    if did is None:
        list_decks(user)
        did = input("Hangi Deste (ID): ")

    if not any(d["id"] == did and d["user_id"] == user["id"] for d in read(FILES["decks"])):
        print("❌ Yetkisiz veya geçersiz deste ID.")
        return

    cid = str(uuid.uuid4())
    cards = read(FILES["cards"])
    new_card = {
        "id": cid,
        "deck_id": did,
        "front": front if front else input("Soru (Ön yüz): "),
        "back": back if back else input("Cevap (Arka yüz): "),
        "created_at": datetime.now().isoformat()
    }
    cards.append(new_card)
    atomic_write(FILES["cards"], cards)

    srs = read(FILES["srs"])
    srs.append({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "card_id": cid,
        "repetition": 0,
        "interval_days": 1,
        "ef": 2.5,
        "due_date": date.today().isoformat(),
        "last_quality": None
    })
    atomic_write(FILES["srs"], srs)
    print("Kart başarıyla eklendi.")
    return new_card


# ================= REVIEW (SM-2) =================
def review(user):
    today = date.today()
    srs_list = read(FILES["srs"])
    cards = read(FILES["cards"])
    due = [s for s in srs_list if s["user_id"] == user["id"] and date.fromisoformat(s["due_date"]) <= today]

    if not due:
        print("🎉 Bugün için çalışılacak kart yok!")
        return

    for s in due:
        try:
            c = next(c for c in cards if c["id"] == s["card_id"])
            print(f"\nSoru: {c['front']}")
            input("Cevabı görmek için ENTER tuşuna basın...")
            print(f"Cevap: {c['back']}")

            q_input = input("Kalite Puanı (0-5): ")
            q = int(q_input) if q_input.isdigit() and 0 <= int(q_input) <= 5 else 0

            # SM-2 Formülü
            ef = max(1.3, s["ef"] + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
            if q < 3:
                rep, interval = 0, 1
            else:
                rep = s["repetition"] + 1
                if rep == 1:
                    interval = 1
                elif rep == 2:
                    interval = 6
                else:
                    interval = round(s["interval_days"] * ef)

            s.update({
                "repetition": rep,
                "interval_days": interval,
                "ef": ef,
                "due_date": (today + timedelta(days=interval)).isoformat(),
                "last_quality": q
            })

            rev_logs = read(FILES["reviews"])
            rev_logs.append({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "card_id": c["id"],
                "quality": q,
                "reviewed_at": datetime.now().isoformat()
            })
            atomic_write(FILES["reviews"], rev_logs)
            atomic_write(FILES["srs"], srs_list)
            print(f"Güncellendi. Bir sonraki tekrar: {s['due_date']}")

        except StopIteration:
            continue


# ================= TEST HELPERS =================
def _register_test(email, pwd): return register(email, pwd)


def _login_test(email, pwd):
    try:
        return login(email, pwd)
    except:
        return None


def _create_deck_test(user, name): return create_deck(user, name)


def _add_card_test(user, did, f, b): return add_card(user, did, f, b)


def _delete_deck_test(user, did): return delete_deck(user, did)


def _due_cards_test(user):
    today = date.today()
    return [s for s in read(FILES["srs"]) if s["user_id"] == user["id"] and date.fromisoformat(s["due_date"]) <= today]


def _review_test(user, card_id, q):
    srs_list = read(FILES["srs"])
    for s in srs_list:
        if s["card_id"] == card_id:
            ef = max(1.3, s["ef"] + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
            if q < 3:
                rep, interval = 0, 1
            else:
                rep = s["repetition"] + 1
                interval = 1 if rep == 1 else 6 if rep == 2 else round(s["interval_days"] * ef)
            s.update({"repetition": rep, "interval_days": interval, "ef": ef,
                      "due_date": (date.today() + timedelta(days=interval)).isoformat(), "last_quality": q})
    atomic_write(FILES["srs"], srs_list)


# ================= MAIN =================
def main():
    init_storage()
    user = None
    print("--- StudyBuddy CLI ---")

    while not user:
        print("\n1) Kayıt Ol\n2) Giriş Yap\n3) Çıkış")
        choice = input("> ")
        try:
            if choice == "1":
                user = register()
            elif choice == "2":
                user = login()
            elif choice == "3":
                return
        except ValueError as e:
            print(f"❌ {e}")

    while True:
        print(f"\nMenü ({user['email']})")
        print("1) Deste Oluştur  2) Deste Listele  3) Deste Sil")
        print("4) Kart Ekle       5) Bugün Çalış     6) Rapor")
        print("7) Yedekle         8) Çıkış")

        c = input("> ")
        if c == "1":
            create_deck(user)
        elif c == "2":
            list_decks(user)
        elif c == "3":
            delete_deck(user)
        elif c == "4":
            add_card(user)
        elif c == "5":
            review(user)
        elif c == "6":
            revs = [r for r in read(FILES["reviews"]) if r["user_id"] == user["id"]]
            print(f"Toplam çalışma: {len(revs)}")
        elif c == "7":
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.make_archive(name, "zip", DATA)
            print(f"Yedek: {name}.zip")
        elif c == "8":
            break


if __name__ == "__main__":
    main()