import unittest
import main
import os
import shutil
from pathlib import Path
from datetime import date


class TestStudyBuddy(unittest.TestCase):

    def setUp(self):
        """Her testten önce temiz bir test verisi oluşturur."""
        # Test için geçici bir klasör kullanıyoruz ki gerçek verilerin bozulmasın
        main.DATA = Path("test_data")
        main.FILES = {k: main.DATA / v.name for k, v in main.FILES.items()}

        if main.DATA.exists():
            shutil.rmtree(main.DATA)
        main.init_storage()

    def tearDown(self):
        """Test bittikten sonra test verilerini temizler."""
        if main.DATA.exists():
            shutil.rmtree(main.DATA)

    # 1️⃣ Kayıt Testi: Aynı email ile ikinci kayıt engellenir
    def test_register_same_email_blocked(self):
        main._register_test("test@test.com", "1234")
        with self.assertRaises(ValueError):
            main._register_test("test@test.com", "5678")

    # 2️⃣ Giriş Testi: Yanlış parola reddedilir
    def test_login_wrong_password(self):
        main._register_test("a@a.com", "1234")
        user = main._login_test("a@a.com", "wrong_pass")
        self.assertIsNone(user)

    # 3️⃣ Deck CRUD: Oluşturma kontrolü
    def test_create_deck(self):
        user = main._register_test("u@u.com", "1234")
        deck = main._create_deck_test(user, "Python")
        self.assertEqual(deck["name"], "Python")
        self.assertEqual(len(main.read(main.FILES["decks"])), 1)

    # 4️⃣ Cascade Silme: Deck silince kartlar ve SRS silinir
    def test_delete_deck_cascade(self):
        user = main._register_test("u@u.com", "1234")
        deck = main._create_deck_test(user, "Python")
        card = main._add_card_test(user, deck["id"], "Soru", "Cevap")

        # Silmeden önce 1 kart olmalı
        self.assertEqual(len(main.read(main.FILES["cards"])), 1)

        main._delete_deck_test(user, deck["id"])

        # Silindikten sonra kartlar ve SRS boş olmalı
        self.assertEqual(len(main.read(main.FILES["cards"])), 0)
        self.assertEqual(len(main.read(main.FILES["srs"])), 0)

    # 5️⃣ SRS Mantığı: Kart eklenince SRS kaydı oluşur
    def test_card_creates_srs(self):
        user = main._register_test("u@u.com", "1234")
        deck = main._create_deck_test(user, "Python")
        card = main._add_card_test(user, deck["id"], "Nedir?", "Budur.")

        srs = main.read(main.FILES["srs"])
        self.assertEqual(len(srs), 1)
        self.assertEqual(srs[0]["card_id"], card["id"])
        self.assertEqual(srs[0]["ef"], 2.5)  # Başlangıç EF değeri

    # 6️⃣ SM-2 Algoritması: Düşük kalite (q<3) tekrarı sıfırlar
    def test_review_low_quality_resets(self):
        user = main._register_test("u@u.com", "1234")
        deck = main._create_deck_test(user, "Python")
        card = main._add_card_test(user, deck["id"], "Q", "A")

        # Önce başarılı bir çalışma yapalım (repetition artsın)
        main._review_test(user, card["id"], 5)
        # Sonra başarısız (0 puan) verelim
        main._review_test(user, card["id"], 0)

        srs = main.read(main.FILES["srs"])[0]
        self.assertEqual(srs["repetition"], 0)
        self.assertEqual(srs["interval_days"], 1)

    # 7️⃣ SM-2 Algoritması: Yüksek kalite (q>=3) intervali büyütür
    def test_review_high_quality_increases_interval(self):
        user = main._register_test("u@u.com", "1234")
        deck = main._create_deck_test(user, "Python")
        card = main._add_card_test(user, deck["id"], "Q", "A")

        # 1. tekrar (5 puan)
        main._review_test(user, card["id"], 5)
        srs1 = main.read(main.FILES["srs"])[0]
        self.assertEqual(srs1["interval_days"], 1)

        # 2. tekrar (5 puan)
        main._review_test(user, card["id"], 5)
        srs2 = main.read(main.FILES["srs"])[0]
        self.assertEqual(srs2["interval_days"], 6)

    # 8️⃣ İzolasyon Testi: Kullanıcılar birbirinin verisini göremez
    def test_user_isolation(self):
        u1 = main._register_test("u1@test.com", "123")
        u2 = main._register_test("u2@test.com", "123")

        main._create_deck_test(u1, "U1 Deck")

        # u2'nin destelerini listelediğimizde boş gelmeli
        u2_decks = [d for d in main.read(main.FILES["decks"]) if d["user_id"] == u2["id"]]
        self.assertEqual(len(u2_decks), 0)

    # 9️⃣ Due List: Bugünün tarihi gelen kartlar listelenir
    def test_due_cards_logic(self):
        user = main._register_test("u@u.com", "1234")
        deck = main._create_deck_test(user, "Python")
        main._add_card_test(user, deck["id"], "Soru", "Cevap")

        due = main._due_cards_test(user)
        self.assertEqual(len(due), 1)


if __name__ == "__main__":
    unittest.main()