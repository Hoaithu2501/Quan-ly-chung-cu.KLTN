"""Small, deterministic Vietnamese retrieval over content managed by administrators.

Scores reflect the question's specific intent. Sharing a broad topic never grants
a minimum score, and answer text can only support an already relevant title.
"""

import re
import unicodedata
from functools import lru_cache


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "").lower().replace("đ", "d"))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


# Prefer a full phrase over its contained aliases, but preserve overlapping
# concepts: "gui xe dien" contains both parking and an electric vehicle.
ALIASES = {
    "parking": ("gui xe", "giu xe", "dau xe", "do xe", "de xe", "trong xe", "bai xe"),
    "invoice": ("hoa don",),
    "payment": ("thanh toan", "dong tien", "tra tien", "nop tien"),
    "hotline": ("hotline", "so dien thoai", "so dt", "sdt", "duong day nong"),
    "management": ("ban quan ly", "van phong quan ly", "bql"),
    "pet": ("thu cung", "cho meo", "nuoi cho", "nuoi meo", "vat nuoi"),
    "pharmacy": ("hieu thuoc", "nha thuoc", "mua thuoc"),
    "fire": ("phong chay chua chay", "phong chay", "chua chay", "hoa hoan", "pccc", "chay"),
    "noise": ("tieng on", "gay on", "on ao", "yen tinh", "karaoke"),
    "security": ("camera", "giam sat", "an ninh"),
    "gym": ("phong gym", "phong tap", "the duc"),
    "pool": ("ho boi", "be boi"),
    "garbage": ("rac thai", "do rac", "rac sinh hoat", "rac"),
    "repair": ("sua chua", "bao tri", "hong dien nuoc", "hong dien", "hong nuoc"),
    "complaint": ("khieu nai", "phan anh"),
    "notice": ("thong bao",),
    "elevator": ("thang may",),
    "visitor": ("vang lai", "khach"),
    "overdue": ("qua han", "tre han", "cham dong", "cham tra", "cham thanh toan"),
    "history": ("lich su", "da dong", "da tra"),
    "methods": ("hinh thuc", "phuong thuc", "bang cach nao"),
    "receipt": ("hoa don dien tu", "bien nhan", "bien lai", "chung tu"),
    "due": ("han thanh toan", "han dong", "han tra", "ngay nao phai dong", "han nop"),
    "issue": ("phat hanh", "lap hoa don", "tao hoa don"),
    "register": ("dang ky", "dang ki"),
    "cancel": ("huy", "ngung gui", "dung gui"),
    "duration": ("toi thieu", "cam ket", "it nhat"),
    "hours": ("gio lam viec", "gio mo cua", "gio dong cua", "gio hoat dong"),
    "limit": ("toi da", "gioi han", "bao nhieu xe"),
    "price": (
        "het bao nhieu tien",
        "ton bao nhieu tien",
        "mat bao nhieu tien",
        "ton may tien",
        "mat may tien",
        "het may tien",
        "het bao nhieu",
        "ton bao nhieu",
        "mat bao nhieu",
        "bao nhieu tien",
        "bao nhieu dong",
        "may tien",
        "nhieu tien",
        "nhiu tien",
        "bn tien",
        "may dong",
        "bao nhieu",
        "chi phi",
        "muc phi",
        "bang gia",
        "gia ve",
        "gia",
    ),
    "fee": ("phi",),
    "collection": ("thu khi nao", "thu nhu the nao", "ky thu", "lich thu"),
    "motorbike": ("xe may",),
    "electricbike": ("xe may dien", "xe dap dien", "xe chay dien", "xe dien"),
    "bicycle": (
        "xe dap thuong",
        "xe dap",
    ),
    "car": ("o to", "xe hoi"),
    "card": (
        "lam the",
        "the gui xe",
    ),
    "servicefee": ("phi dich vu",),
    "acceptedtypes": ("nhung loai xe", "loai xe nao", "loai phuong tien", "nhan gui"),
}
REPLACEMENTS = sorted(
    ((phrase, key) for key, phrases in ALIASES.items() for phrase in phrases),
    key=lambda item: len(item[0]),
    reverse=True,
)
ALIAS_PATTERNS = [(re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"), key) for phrase, key in REPLACEMENTS]
STOP_WORDS = set(
    "toi minh ban cho hoi co duoc khong la thi va cua o cac nhung mot nhu the nao gi voi can biet xin hay lam the thuoc chung cu khi neu sao de trong tai den ve nay bao vui long em anh chi a nhe nhi vay chu giup nho muon thac mac".split()
)
VEHICLES = {"motorbike", "electricbike", "bicycle", "car"}
TOPICS = {
    "parking": {"parking", "acceptedtypes", *VEHICLES},
    "billing": {"invoice", "payment", "servicefee", "receipt"},
    "contact": {"hotline", "management"},
    **{
        name: {name}
        for name in (
            "pet",
            "pharmacy",
            "fire",
            "noise",
            "security",
            "gym",
            "pool",
            "garbage",
            "repair",
            "complaint",
            "notice",
            "elevator",
        )
    },
}
INTENTS = {
    "price",
    "hotline",
    "overdue",
    "history",
    "methods",
    "receipt",
    "due",
    "issue",
    "register",
    "cancel",
    "duration",
    "hours",
    "limit",
    "card",
    "collection",
    "acceptedtypes",
}


@lru_cache(maxsize=1024)
def _canonical(value):
    # Preserve the distinction between modal "có thể" and a parking "thẻ";
    # otherwise accent removal creates a false card intent in "có thể gửi xe".
    value = unicodedata.normalize("NFC", str(value or "").lower())
    value = re.sub(r"\b(?:có thể|co the|làm thế nào|lam the nao)\b", " ", value)
    value = normalize(value)
    matches = []
    for pattern, replacement in ALIAS_PATTERNS:
        for match in pattern.finditer(value):
            start, end = match.span()
            if any(left <= start and end <= right for left, right, _ in matches):
                continue
            matches.append((start, end, replacement))
    remainder = list(value)
    for start, end, _ in matches:
        remainder[start:end] = " " * (end - start)
    return " ".join(replacement for _, _, replacement in matches) + " " + "".join(remainder)


def _features(value):
    words = set(_canonical(value).split()) - STOP_WORDS
    normalized = normalize(value)
    if words & VEHICLES:
        # Recognize "duoc de xe" as well as "xe dien duoc de ...".
        action = "parking" in words or bool(
            re.search(
                r"\b(?:gui|giu)\b|\bduoc (?:de|do|dau)\b|"
                r"\b(?:de|do|dau) (?:o|tai|trong|ngoai|duoi|tren)\b",
                normalized,
            )
        )
        if action:
            words.add("parking")
            words -= {"gui", "giu", "dau", "do", "trong"}
        # A plain fee attached to a vehicle also denotes parking cost.
        if "fee" in words:
            words.add("parking")
        permission = bool(re.search(r"\b(?:duoc|cho phep|co the)\b", normalized)) and action
        acceptance = bool(re.search(r"\b(?:co nhan|nhan xe|cho gui|co gui)\b", normalized))
        if (
            (permission or acceptance)
            and "visitor" not in words
            and not words & {"price", "fee", "register", "cancel", "duration", "limit", "collection"}
        ):
            words.add("acceptedtypes")
            words -= {"nhan", "phep"}
    intents = words & INTENTS
    if "fee" in words and not intents & {"collection", "due"}:
        intents.add("price")
    if intents & {"duration", "limit"}:
        intents.discard("price")
    return words, {topic for topic, terms in TOPICS.items() if words & terms}, intents


def _parking_subjects(value):
    """Keep parking permission/prices separate from other vehicle questions."""
    normalized = normalize(value)
    subjects = set()
    for subject, pattern in (
        ("charging", r"\bsac\b"),
        ("battery", r"\bpin\b"),
        ("purchase", r"\b(?:mua|ban|thue)\s+xe\b"),
        ("repair", r"\b(?:sua|hong|bao tri)\b"),
        ("power", r"\b(?:ma luc|dong co|watt)\b"),
        (
            "upstairs",
            r"\b(?:(?:o|trong|len|vao) can ho|(?:trong|len|vao) (?:nha|phong)|"
            r"hanh lang|thang may|san thuong|sanh|loi thoat hiem|cau thang|(?:tren|len) tang)\b",
        ),
    ):
        if re.search(pattern, normalized):
            subjects.add(subject)
    # Accent removal otherwise conflates "độ xe" (customize) with "đỗ xe".
    if re.search(r"\bđộ\s+xe\b", unicodedata.normalize("NFC", str(value).lower())):
        subjects.add("customize")
    return subjects


def _score(question, title, answer="", category=""):
    query, query_topics, query_intents = _features(question)
    target, target_topics, target_intents = _features(title)
    if not query or not target:
        return 0.0
    if normalize(question) == normalize(title):
        return 1.0
    if query_topics & target_topics & {"parking"}:
        if _parking_subjects(question) - _parking_subjects(title):
            return 0.0
        query_vehicles, target_vehicles = query & VEHICLES, target & VEHICLES
        if query_vehicles and target_vehicles and not query_vehicles & target_vehicles:
            return 0.0
    overlap = query & target
    if not overlap:
        return 0.0
    coverage = len(overlap) / len(query)
    precision = len(overlap) / len(target)
    score = 0.60 * coverage + 0.15 * precision
    if query_intents:
        score += 0.20 * len(query_intents & target_intents) / len(query_intents)
        if not query_intents & target_intents:
            score *= 0.55
    if query_topics:
        score += 0.05 * len(query_topics & target_topics) / len(query_topics)
        if target_topics and not query_topics & target_topics:
            score *= 0.55
    # Never match a FAQ just because its long answer contains a popular term.
    if score >= 0.35:
        supporting = _features(answer + " " + category)[0]
        score += 0.04 * len((query - target) & supporting) / len(query)
    return min(score, 1.0)


def _emergency(question):
    value = normalize(question)
    if any(phrase in value for phrase in ("chay bo", "chay xe", "chay may", "chay chuong trinh")) and not any(
        phrase in value for phrase in ("hoa hoan", "khoi", "ngon lua", "bao chay")
    ):
        return False
    prevention = any(phrase in value for phrase in ("phong tranh", "phong ngua", "nguy co", "quy dinh", "tap huan"))
    active = any(phrase in value for phrase in ("dang chay", "bi dien giat", "bi ket", "vua phat hien", "cuu toi"))
    if prevention and not active:
        return False
    incident = (
        "dang chay",
        "co chay",
        "bi chay",
        "hoa hoan",
        "phat hien khoi",
        "khoi day",
        "ngui thay khoi",
        "ro dien",
        "dien giat",
        "ket thang",
        "mac ket",
        "vo ong nuoc",
    )
    return any(phrase in value for phrase in incident) or bool(re.search(r"\bchay (?:thi |phai |lam |roi|o )", value))


def _incident_types(value):
    """Only explicit incident handling qualifies for an emergency answer."""
    if not _emergency(value):
        return set()
    normalized = normalize(value)
    types = set()
    if "chay" in normalized.split() or any(term in normalized for term in ("hoa hoan", "khoi")):
        types.add("fire")
    for incident, phrases in (
        ("electric", ("ro dien", "dien giat")),
        ("trapped", ("ket thang", "mac ket")),
        ("water", ("vo ong nuoc",)),
    ):
        if any(phrase in normalized for phrase in phrases):
            types.add(incident)
    return types


def _location_query(question):
    value = normalize(question)
    position = any(phrase in value for phrase in ("o dau", "vi tri", "tang may", "duong den", "cho nao", "dia diem"))
    # These refer to application actions, not physical places.
    application = any(
        phrase in value
        for phrase in (
            "hoa don",
            "lich su",
            "thong bao",
            "bao hong",
            "bao su co",
            "bao o dau",
            "khieu nai",
            "dang ky",
            "thanh toan",
        )
    )
    return position and not application


def _location_answer(row):
    parts = [row["name"]]
    if row.get("block"):
        parts.append("tòa " + str(row["block"]))
    if row.get("floor"):
        parts.append("tầng " + str(row["floor"]))
    return ", ".join(parts) + "." + (" " + row["description"] if row.get("description") else "")


def retrieve(question, faqs, locations, limit=5):
    """Return attributable matches, or an explicit clarification / empty result.

    FAQ and location dictionaries are read-only inputs. No answer is invented.
    A compound question selects its best answer for each segment. ``matches``
    additionally retains up to five relevant records as grounded LLM context.
    """
    normalized = normalize(question)
    result = {
        "matches": [],
        "selected": [],
        "needs_clarification": False,
        "clarification": None,
        "emergency": _emergency(question),
    }
    incidents = _incident_types(question)
    if (
        not result["emergency"]
        and "tien nha" in normalized
        and not any(term in normalized for term in ("tien thue", "phi dich vu"))
    ):
        result.update(
            needs_clarification=True, clarification="Bạn muốn hỏi tiền thuê căn hộ hay phí dịch vụ của chung cư?"
        )
        return result
    fragments = [question]
    for fragment in re.split(r"\s+và\s+|\s+va\s+|\s+đồng thời\s+|[;?]", question, flags=re.I):
        words, _, intents = _features(fragment)
        if len(words) >= 2 or "hotline" in intents:
            fragments.append(fragment)
    fragments = list(dict.fromkeys(fragments))
    candidates, fragment_best = [], {}
    for source, rows in (("faq", faqs), ("location", locations)):
        for row in rows:
            row = dict(row)
            title = row["question"] if source == "faq" else row["name"]
            answer = row["answer"] if source == "faq" else _location_answer(row)
            if result["emergency"] and (source != "faq" or not incidents & _incident_types(title)):
                # A compound urgent question must never become a routine billing
                # or parking response. Let the caller give its safety fallback
                # when no administrator-managed incident guidance exists.
                continue
            scores = []
            for fragment in fragments:
                location_query = _location_query(fragment)
                if location_query != (source == "location"):
                    continue
                query = fragment
                if location_query:
                    query = re.sub(r"\b(o dau|vi tri|tang may|duong den|cho nao|dia diem)\b", "", normalize(fragment))
                score = _score(query, title, answer, row.get("category") or "")
                if _incident_types(fragment) & _incident_types(title):
                    score = max(score, 0.90)
                # A physical name may live in a description (e.g. a pharmacy's
                # trade name). Require substantial lexical coverage, not topic alone.
                if source == "location" and score < 0.48:
                    words, _, _ = _features(query)
                    description_words = _features(row.get("description") or "")[0]
                    if len(words) >= 2 and words <= description_words:
                        score = 0.55
                scores.append((score, fragment))
            if not scores:
                continue
            score, fragment = max(scores, key=lambda pair: pair[0])
            if score < 0.48:
                continue
            match = {
                "source": source,
                "source_id": row.get("faq_id") if source == "faq" else row.get("location_id"),
                "source_title": title,
                "answer": answer,
                "confidence": round(score, 3),
            }
            candidates.append((score, str(row.get("faq_id", row.get("location_id", ""))), match))
            for fragment_score, fragment in scores:
                if fragment_score >= 0.48 and fragment_score > fragment_best.get(fragment, (0, None))[0]:
                    fragment_best[fragment] = (fragment_score, match)
    candidates.sort(key=lambda candidate: (-candidate[0], candidate[1]))
    answers = set()
    for _, _, match in candidates:
        answer = normalize(match["answer"])
        if answer in answers:
            continue
        answers.add(answer)
        result["matches"].append(match)
        if len(result["matches"]) >= max(1, min(limit, 5)):
            break
    answers = set()
    for fragment in fragments:
        if fragment not in fragment_best:
            continue
        _, match = fragment_best[fragment]
        answer = normalize(match["answer"])
        if answer not in answers:
            result["selected"].append(match)
            answers.add(answer)
        if len(result["selected"]) >= max(1, min(limit, 5)):
            break
    return result
