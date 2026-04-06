from __future__ import annotations

import re
from typing import Any


EXACT_RU_TRANSLATIONS = {
    "Bosh Admin": "Главный администратор",
    "Admin": "Администратор",
    "Omborchi": "Кладовщик",
    "Ishlab chiqarish ustasi": "Мастер производства",
    "CNC operatori": "Оператор CNC",
    "Pardozlovchi": "Отделочник",
    "Chiqindi operatori": "Оператор отходов",
    "Sotuv menejeri": "Менеджер по продажам",
    "Kuryer": "Курьер",
    "Kutilmoqda": "Ожидает",
    "Rejalashtirilgan": "Запланировано",
    "Jarayonda": "В процессе",
    "Tugallangan": "Завершено",
    "Bekor qilingan": "Отменено",
    "Aktiv": "Активно",
    "To‘xtatilgan": "Приостановлено",
    "To'xtatilgan": "Приостановлено",
    "Tayyor": "Готово",
    "Brak": "Брак",
    "Band qilingan": "Зарезервировано",
    "Sotilgan": "Продано",
    "Tasdiqlandi": "Подтверждено",
    "Rad etildi (Brak)": "Отклонено (брак)",
    "Kunlik": "Дневная",
    "Tungi": "Ночная",
    "Shoshilinch": "Срочно",
    "Yuqori": "Высокий",
    "O‘rtacha": "Средний",
    "O'rtacha": "Средний",
    "Past": "Низкий",
    "Hisobot fayli topilmadi": "Файл отчета не найден",
    "Stage is required": "Требуется этап",
    "Hujjat topilmadi": "Документ не найден",
    "Partiya topilmadi": "Партия не найдена",
    "QR kod tanilmadi": "QR-код не распознан",
    "courier_id is required": "Требуется courier_id",
    "Courier not found": "Курьер не найден",
    "O'chirish taqiqlangan. Ma'lumotlarni bekor qilish yoki status orqali yopish kerak.": "Удаление запрещено. Запись нужно отменить или закрыть через статус.",
    "Kesish uchun mavjud blok qolmagan.": "Не осталось доступных блоков для резки.",
    "Tayyor mahsulot miqdori rejalashtirilgan miqdordan oshib ketdi.": "Количество готовой продукции превысило план.",
    "Bunker tanlanmagan.": "Бункер не выбран.",
    "Yuklanadigan Zames topilmadi.": "Не найден замес для загрузки.",
    "WIP Limit: Hozirda 2 ta aktiv Zames mavjud. Navbat kuting.": "Лимит WIP: сейчас активны 2 замеса. Дождитесь очереди.",
    "Xom Ashyo (Sklad 1)": "Сырье (Склад 1)",
    "Bloklar (Sklad 2)": "Блоки (Склад 2)",
    "Yarim Tayyor (Sklad 3)": "Полуфабрикат (Склад 3)",
    "Tayyor Mahsulot (Sklad 4)": "Готовая продукция (Склад 4)",
    "Chiqindi": "Отходы",
    "Xom ashyo kirimi": "Поступление сырья",
    "Ishlab chiqarilgan": "Произведено",
    "Sotuvlar soni": "Количество продаж",
    "Hujjatlar Statistikasi": "Статистика документов",
    "Ishlab Chiqarish Zanjiri (Pipeline)": "Производственная цепочка (Pipeline)",
    "Zames": "Замес",
    "Formovka": "Формовка",
    "Quritish": "Сушка",
    "Bunker": "Бункер",
    "Tayyor bloklar": "Готовые блоки",
    "Pardozlangan": "Отделано",
    "Brak/Chiqindi": "Брак/отходы",
    "Bugungi Sotuv": "Продажи за сегодня",
    "Aktiv Buyurtmalar": "Активные заказы",
    "Mijozlar Soni": "Количество клиентов",
    "Umumiy Qarzdorlik": "Общая задолженность",
    "Oylik Ishlab Chiqarish": "Месячное производство",
    "Oylik Sotuv": "Месячные продажи",
    "Chiqindi Ulushi": "Доля отходов",
    "Yetkazib beruvchi": "Поставщик",
    "Xom Ashyo (Granula)": "Сырье (гранула)",
    "Bugungi Natija": "Результат за сегодня",
    "Umumiy Chiqindi": "Общий объем отходов",
    "Kutilayotgan ishlar": "Ожидающие задачи",
    "Hisob-faktura": "Счет-фактура",
    "Nakladnoy": "Накладная",
    "Buyurtma-naryad": "Заказ-наряд",
    "Boshqa": "Прочее",
    "Qoralama": "Черновик",
    "Hujjat": "Документ",
    "Partiya": "Партия",
    "Mijoz": "Клиент",
    "Sotuvlar": "Продажи",
    "Moliya": "Финансы",
    "Ishlab chiqarish": "Производство",
    "Hujjatlar": "Документы",
    "Tizim bo'ylab to'liq boshqaruv, nazorat va konfiguratsiya.": "Полное управление, контроль и настройка по всей системе.",
    "Operatsion boshqaruv, xodimlar, hujjatlar va jarayon nazorati.": "Операционное управление, сотрудники, документы и контроль процессов.",
    "Sklad kirim-chiqimi, transferlar va qoldiq nazorati.": "Приход-расход склада, переводы и контроль остатков.",
    "Zames, quritish, formovka va ishlab chiqarish oqimini boshqarish.": "Управление замесом, сушкой, формовкой и производственным потоком.",
    "Kesish buyurtmalari va CNC ishlab chiqarish vazifalari.": "Заказы на резку и производственные задачи CNC.",
    "Armirlash, shpaklyovka va tayyor dekor jarayonlari.": "Армирование, шпаклевка и процессы готового декора.",
    "Chiqindi qabul qilish, qayta ishlash va yo'qotish nazorati.": "Прием отходов, переработка и контроль потерь.",
    "Mijozlar, invoice, yetkazib berish va sotuv yakunlash.": "Клиенты, счета, доставка и завершение продаж.",
    "Waybill, yetkazib berish va topshirish tasdiqlari.": "Waybill, доставка и подтверждение передачи.",
    "Rol bo'yicha vazifalar hali aniqlanmagan.": "Задачи для этой роли пока не определены.",
}

EXACT_MAP_RU = {
    re.sub(r"\s+", " ", key.replace("’", "'").replace("ʻ", "'").replace("`", "'")).strip(): value
    for key, value in EXACT_RU_TRANSLATIONS.items()
}

RU_DYNAMIC_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^([+-]?\d[\d\s.,]*)\s*kg$"), r"\1 кг"),
    (re.compile(r"^([+-]?\d[\d\s.,]*)\s*dona$"), r"\1 шт"),
    (re.compile(r"^([+-]?\d[\d\s.,]*)\s*ta$"), r"\1 шт"),
    (re.compile(r"^([+-]?\d[\d\s.,]*)\s*m3$"), r"\1 м3"),
    (re.compile(r"^([+-]?\d[\d\s.,]*)\s*m³$"), r"\1 м³"),
    (re.compile(r"^Bunker №(.+) band\. Boshqa bunker tanlang\.$"), r"Бункер №\1 занят. Выберите другой бункер."),
    (re.compile(r"^Bosqichni boshlab bo'lmaydi\. Joriy holat: (.+)$"), r"Нельзя запустить этап. Текущий статус: \1"),
    (re.compile(r"^Oldingi bosqich \((.+)\) hali yakunlanmagan\.$"), r"Предыдущий этап (\1) еще не завершен."),
    (re.compile(r"^finished_qty manfiy bo'lishi mumkin emas\.$"), r"finished_qty не может быть отрицательным."),
    (re.compile(r"^waste_m3 manfiy bo'lishi mumkin emas\.$"), r"waste_m3 не может быть отрицательным."),
    (re.compile(r"^Sifat nazorati: (.+) -> (.+)\. ?(.*)$"), r"Контроль качества: \1 -> \2. \3"),
    (re.compile(r"^Muvaffaqiyatli: (.+)$"), r"Успешно: \1"),
    (re.compile(r"^Amal muvaffaqiyatli: (.+)$"), r"Операция выполнена: \1"),
    (re.compile(r"^(.+)\s+sexiga uzatildi$"), r"Передано в цех \1"),
    (re.compile(r"^([+-]?\d[\d\s.,]*)\s*kg qayta ishlandi$"), r"\1 кг переработано"),
]


def canonicalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("ʻ", "'").replace("`", "'")).strip()


def should_translate_request(request) -> bool:
    header = (request.headers.get("Accept-Language") or request.META.get("HTTP_ACCEPT_LANGUAGE") or "").lower()
    return header.startswith("ru")


def translate_text(value: str) -> str:
    if not value:
        return value

    exact = EXACT_MAP_RU.get(canonicalize(value))
    if exact:
        return exact

    for pattern, replacement in RU_DYNAMIC_RULES:
        if pattern.match(value):
            return pattern.sub(replacement, value)

    return value


def translate_payload(value: Any) -> Any:
    if isinstance(value, str):
        return translate_text(value)
    if isinstance(value, list):
        return [translate_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: translate_payload(item) for key, item in value.items()}
    return value
