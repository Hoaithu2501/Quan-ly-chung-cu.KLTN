"""OpenAPI metadata only: this module never changes request validation or access."""

from copy import deepcopy


def string(**kwargs):
    return {"type": "string", **kwargs}


def number(**kwargs):
    return {"type": "integer", "minimum": 0, **kwargs}


def choice(*values):
    return string(enum=list(values))


def object_schema(properties, required=()):
    result = {"type": "object", "properties": properties}
    if required:
        result["required"] = list(required)
    return result


ID = number(minimum=1)
DATE = string(format="date", example="2026-11-10")
MONEY = number(description="Số nguyên VND; không nhập dấu phân cách hoặc số thập phân.")
ROLE = choice("admin", "resident", "technician")
USER = {
    "username": string(minLength=3, maxLength=60, pattern=r"^[A-Za-z0-9_.-]+$"),
    "password": string(format="password", minLength=6, maxLength=30),
    "email": string(format="email", nullable=True),
    "phone": string(nullable=True),
    "role": ROLE,
}
APARTMENT = {
    "code": string(maxLength=30),
    "block": string(maxLength=30),
    "floor": number(minimum=-5),
    "area": {"type": "number", "exclusiveMinimum": True, "minimum": 0, "maximum": 10000},
}
RESIDENT = {
    "user_id": {**ID, "nullable": True},
    "full_name": string(maxLength=120),
    "id_card": string(nullable=True),
    "phone": string(nullable=True),
    "relation_type": choice("owner", "tenant"),
    "registered_apartment_code": string(
        maxLength=30, nullable=True, description="Mã căn hộ người dùng khai báo; không tự cấp quyền truy cập."
    ),
}
VERIFIED_APARTMENT = object_schema(
    {
        "apartment_id": ID,
        "code": string(),
        "confirmed_by_user_id": ID,
        "confirmed_at": string(description="Thời điểm Ban quản lý xác nhận cư trú do server lưu."),
    },
    ("apartment_id", "code", "confirmed_by_user_id", "confirmed_at"),
)
RESIDENT_PROFILE = object_schema(
    {
        **RESIDENT,
        "resident_id": ID,
        "apartment_ids": {
            "type": "array",
            "items": ID,
            "description": "Phạm vi căn hộ: hợp đồng còn hiệu lực hoặc xác nhận cư trú của Ban quản lý.",
        },
        "apartment_codes": {"type": "array", "items": string()},
        "contract_apartment_ids": {
            "type": "array",
            "items": ID,
            "description": "Chỉ căn hộ theo hợp đồng đang có hiệu lực thực tế.",
        },
        "verified_apartment_ids": {
            "type": "array",
            "items": ID,
            "description": "Chỉ liên kết cư trú được Ban quản lý xác nhận riêng.",
        },
        "verified_apartments": {"type": "array", "items": VERIFIED_APARTMENT},
    },
    (
        "resident_id",
        "full_name",
        "apartment_ids",
        "apartment_codes",
        "contract_apartment_ids",
        "verified_apartment_ids",
        "verified_apartments",
    ),
)
CONTRACT = {
    "apartment_id": ID,
    "resident_id": ID,
    "contract_type": choice("ownership", "rental"),
    "start_date": DATE,
    "end_date": {**DATE, "nullable": True, "description": "Bắt buộc với hợp đồng rental."},
    "status": choice("active", "expired", "terminated"),
}
INVOICE_BASE = {"apartment_id": ID, "period": string(), "due_date": DATE}
MONTHLY = {
    **INVOICE_BASE,
    "period": string(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    "electricity_usage": {
        "type": "number",
        "minimum": 0,
        "maximum": 1000000,
        "multipleOf": 0.001,
        "description": "Điện tiêu thụ trong kỳ (kWh).",
    },
    "water_usage": {
        "type": "number",
        "minimum": 0,
        "maximum": 1000000,
        "multipleOf": 0.001,
        "description": "Nước tiêu thụ trong kỳ (m³).",
    },
    "electricity_unit_price": {**MONEY, "minimum": 1, "description": "Đơn giá VNĐ/kWh."},
    "water_unit_price": {**MONEY, "minimum": 1, "description": "Đơn giá VNĐ/m³."},
    "electricity_fee": MONEY,
    "water_fee": MONEY,
    "total_amount": {**MONEY, "description": "Tùy chọn; nếu gửi phải bằng điện + nước. Server tự tính."},
}
SEMIANNUAL = {
    **INVOICE_BASE,
    "period": string(pattern=r"^\d{4}-H[12]$"),
    "service_fee": MONEY,
    "parking_fee": {**MONEY, "description": "Bỏ qua để tính các tháng gửi xe trong kỳ cùng phí thẻ phát hành lần đầu."},
    "total_amount": {**MONEY, "description": "Tùy chọn; nếu gửi phải bằng dịch vụ + gửi xe."},
}
VEHICLE = {
    "apartment_id": ID,
    "vehicle_type": choice("bicycle", "motorbike", "electric_bike"),
    "plate_number": string(
        nullable=True, description="Bắt buộc với xe máy và xe điện. Xe đạp để trống được cấp mã theo căn hộ."
    ),
    "monthly_fee": {**MONEY, "description": "Tùy chọn; phải đúng mức cố định: xe đạp 50000, xe máy/xe điện 100000."},
    "registration_months": number(minimum=2, default=2, description="Số tháng cam kết tối thiểu trước khi được hủy."),
    "registered_date": DATE,
    "status": choice("active", "cancelled"),
}
TECHNICIAN = {"user_id": ID, "full_name": string(), "specialty": choice("parking", "payment", "general")}
TICKET = {
    "apartment_id": {**ID, "nullable": True},
    "technician_id": {**ID, "nullable": True},
    "type": choice("repair", "maintenance", "cut_service", "restore_service"),
    "description": string(),
    "priority": choice("low", "medium", "high"),
    "status": choice("pending", "in_progress", "completed"),
}
NOTICE = {
    "type": choice("general", "private"),
    "title": string(maxLength=250),
    "content": string(maxLength=10000),
    "target_apartment_id": ID,
    "target_role": choice("admin"),
    "target_resident_id": {
        **ID,
        "description": "Thông báo riêng chỉ cho cư dân này; không chọn đồng thời căn hộ hoặc vai trò.",
    },
}
FAQ = {"category": string(nullable=True), "question": string(maxLength=1500), "answer": string(maxLength=10000)}
LOCATION = {
    "name": string(),
    "block": string(nullable=True),
    "floor": string(nullable=True),
    "description": string(nullable=True),
}
PAYMENT_ORDER = object_schema(
    {
        "order_id": string(pattern=r"^VQR-[A-Za-z0-9_-]+$"),
        "invoice_type": choice("monthly", "semiannual"),
        "invoice_id": ID,
        "amount": MONEY,
        "mode": choice("sepay"),
        "environment": choice("test", "live"),
        "status": choice("pending", "awaiting_confirmation", "success", "expired", "cancelled"),
        "payer_user_id": ID,
        "is_owner": {"type": "boolean"},
        "can_pay": {"type": "boolean"},
        "paid_amount": MONEY,
        "remaining_amount": MONEY,
        "payment_id": {**ID, "nullable": True},
        "created_at": string(format="date-time"),
        "expires_at": string(format="date-time"),
        "invoice_created_at": string(
            nullable=True, description="Thời gian lập hóa đơn; dấu thời gian SQLite không có offset là UTC."
        ),
        "paid_at": string(nullable=True, description="Thời gian server ghi nhận đủ tiền; null nếu chưa thanh toán."),
        "transfer_content": string(
            nullable=True, description="Chỉ cung cấp cho người giữ phiên còn được chuyển khoản."
        ),
        "qr_image_url": string(nullable=True, description="Đường dẫn cùng origin, cần JWT của người giữ phiên."),
        "receipt_url": string(nullable=True),
        "message": string(),
        "bank": {
            **object_schema({"code": string(), "name": string(), "account_number": string(), "account_name": string()}),
            "nullable": True,
        },
    },
    (
        "order_id",
        "invoice_type",
        "invoice_id",
        "amount",
        "mode",
        "environment",
        "status",
        "is_owner",
        "can_pay",
        "paid_amount",
        "remaining_amount",
    ),
)
BANK_TRANSACTION = object_schema(
    {
        "transaction_id": ID,
        "environment": choice("test", "live"),
        "amount": MONEY,
        "allocated_amount": MONEY,
        "unallocated_amount": MONEY,
        "status": choice("matched", "partial", "overpaid", "duplicate", "unmatched", "ignored"),
        "issue": string(),
        "invoice_type": {**choice("monthly", "semiannual"), "nullable": True},
        "invoice_id": {**ID, "nullable": True},
        "reference": string(),
        "bank_reference": string(),
        "received_at": string(),
        "resolution": {**choice("refunded", "retained", "reviewed"), "nullable": True},
        "resolution_note": string(nullable=True),
    },
    ("transaction_id", "amount", "allocated_amount", "unallocated_amount", "status"),
)


# (schema properties, required on POST, representative JSON). PATCH examples
# keep the same field definitions but remove required fields automatically.
RESOURCES = {
    "/api/apartments": (
        APARTMENT,
        ("code", "block", "floor", "area"),
        {"code": "A-1201", "block": "A", "floor": 12, "area": 72.5},
    ),
    "/api/residents": (
        RESIDENT,
        ("full_name", "relation_type"),
        {"full_name": "Nguyễn Minh An", "relation_type": "tenant", "phone": "0901234567"},
    ),
    "/api/residents/provision": (
        RESIDENT,
        ("full_name", "relation_type"),
        {"user_id": 3, "full_name": "Nguyễn Minh An", "relation_type": "tenant"},
    ),
    "/api/contracts": (
        CONTRACT,
        ("apartment_id", "resident_id", "contract_type", "start_date"),
        {
            "apartment_id": 1,
            "resident_id": 1,
            "contract_type": "rental",
            "start_date": "2026-10-01",
            "end_date": "2027-09-30",
            "status": "active",
        },
    ),
    "/api/parking/vehicles": (
        VEHICLE,
        ("apartment_id", "vehicle_type"),
        {"apartment_id": 1, "vehicle_type": "motorbike", "plate_number": "59A1-12345", "registration_months": 2},
    ),
    "/api/parking/guest-daily": (
        {"parking_date": DATE, "daily_revenue": MONEY},
        ("parking_date", "daily_revenue"),
        {"parking_date": "2026-10-04", "daily_revenue": 250000},
    ),
    "/api/maintenance/technicians": (
        TECHNICIAN,
        ("user_id", "full_name", "specialty"),
        {"user_id": 11, "full_name": "Trần Văn Bình", "specialty": "general"},
    ),
    "/api/maintenance/tickets": (
        TICKET,
        ("description",),
        {"apartment_id": 1, "type": "repair", "description": "Vòi nước bị rò rỉ", "priority": "medium"},
    ),
    "/api/notifications": (
        NOTICE,
        ("type", "title", "content"),
        {"type": "general", "title": "Bảo trì thang máy", "content": "Bảo trì thang máy tòa A từ 09:00 đến 11:00."},
    ),
    "/api/chatbot/faqs": (
        FAQ,
        ("question", "answer"),
        {"category": "Gửi xe", "question": "Đăng ký gửi xe ở đâu?", "answer": "Gửi đơn đăng ký trên cổng cư dân."},
    ),
    "/api/chatbot/locations": (
        LOCATION,
        ("name",),
        {"name": "Phòng camera", "block": "A", "floor": "1", "description": "Cạnh quầy lễ tân."},
    ),
}

PUBLIC = {("POST", "/api/auth/login"), ("POST", "/api/auth/register")}
INTERNAL = {
    "/api/residents/provision",
    "/api/notifications/events",
    "/api/maintenance/technicians/accounts/{user_id}",
}
DUAL_AUTH_GET = {
    "/api/auth/users",
    "/api/apartments",
    "/api/apartments/{apartment_id}",
    "/api/residents",
    "/api/residents/{resident_id}",
    "/api/parking/vehicles",
    "/api/parking/summary",
}
SECURITY_SCHEMES = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT lấy từ login/register. Trạng thái tài khoản được kiểm tra qua Auth.",
    },
    "ServiceToken": {
        "type": "apiKey",
        "in": "header",
        "name": "X-Service-Token",
        "description": "Chỉ dùng cho service nội bộ trên cổng trực tiếp; gateway loại bỏ header này.",
    },
    "SePayWebhookAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Nhập Apikey <khóa webhook riêng>. Không dùng JWT hoặc token API Access.",
    },
}


def request_body(operation, properties, required, example, *, schema=None):
    operation["requestBody"] = {
        "required": True,
        "content": {"application/json": {"schema": schema or object_schema(properties, required), "example": example}},
    }


def query(operation, name, schema, description=""):
    operation.setdefault("parameters", []).append(
        {"name": name, "in": "query", "required": False, "description": description, "schema": schema}
    )


def enrich_operation(path, method, operation):
    """Return a fresh operation so requests cannot mutate global metadata."""
    operation = deepcopy(operation)
    operation["tags"] = [path.split("/")[2]]
    operation["operationId"] = (
        method.lower() + "_" + path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    )
    operation["responses"].update(
        {
            "404": {"description": "Không tìm thấy"},
            "409": {"description": "Trùng dữ liệu hoặc xung đột trạng thái"},
            "503": {"description": "Service liên quan hoặc cấu hình chưa sẵn sàng"},
        }
    )
    for parameter in operation.get("parameters", []):
        if parameter["name"].endswith("_id") and parameter["name"] != "order_id":
            parameter["schema"] = ID
        if parameter["name"] == "kind":
            parameter["schema"] = choice("monthly", "semiannual")
            parameter["example"] = "monthly"
    if (method, path) in PUBLIC:
        operation["security"] = []
    elif path in INTERNAL:
        operation["security"] = [{"ServiceToken": []}]
        operation["description"] = "API nội bộ. Gọi trực tiếp service với X-Service-Token; không dùng JWT cư dân."
    elif method == "GET" and path in DUAL_AUTH_GET:
        operation["security"] = [{"BearerAuth": []}, {"ServiceToken": []}]

    resource_path = path.rsplit("/", 1)[0] if path.endswith("}") else path
    if resource_path in RESOURCES and method in ("POST", "PATCH", "PUT"):
        properties, required, example = RESOURCES[resource_path]
        request_body(operation, properties, required if method == "POST" else (), example)
        if method == "POST":
            operation["responses"]["201"] = {"description": "Đã tạo bản ghi"}

    if path == "/api/auth/login":
        request_body(
            operation,
            {key: USER[key] for key in ("username", "password")},
            ("username", "password"),
            {"username": "admin", "password": "<mật khẩu của bạn>"},
        )
        operation["description"] = (
            "Đăng nhập nhận token JWT. Quá 10 lần sai cho một tài khoản từ một địa chỉ trong 5 phút trả 429."
        )
        operation["responses"]["429"] = {"description": "Quá nhiều lần đăng nhập sai"}
    elif path == "/api/auth/register":
        request_body(
            operation,
            {**USER, "full_name": string(minLength=2, maxLength=50), "role": choice("resident")},
            ("username", "password", "full_name"),
            {"username": "resident_new", "password": "ReplaceMe!2026", "full_name": "Nguyễn Minh An"},
        )
        operation["description"] = "Tạo tài khoản cư dân và hồ sơ qua Resident Service; không tự gán căn hộ."
        operation["responses"]["201"] = {"description": "Đã tạo tài khoản; trả token và user"}
    elif path == "/api/auth/users/{user_id}" and method == "PATCH":
        request_body(operation, {"role": ROLE}, ("role",), {"role": "technician"})
        operation["description"] = (
            "Chỉ admin. Chỉ đổi vai trò; không đổi được vai trò của chính mình. Phiên cũ của tài khoản hết hiệu lực."
        )

    if path == "/api/residents/{resident_id}/apartments" and method == "POST":
        request_body(
            operation,
            {"apartment_id": ID},
            ("apartment_id",),
            {"apartment_id": 1},
            schema={**object_schema({"apartment_id": ID}, ("apartment_id",)), "additionalProperties": False},
        )
        operation["description"] = (
            "Chỉ admin, sau khi kiểm tra thông tin cư trú. Xác nhận một người cùng ở căn hộ "
            "để họ xem hóa đơn và sử dụng chức năng theo căn hộ; không tạo hoặc sửa hợp đồng. "
            "Mã registered_apartment_code tự khai không cấp quyền."
        )
        for code, description in (
            ("200", "Đã có xác nhận; trả hồ sơ cập nhật"),
            ("201", "Đã xác nhận mới; trả hồ sơ cập nhật"),
        ):
            operation["responses"][code] = {
                "description": description,
                "content": {"application/json": {"schema": RESIDENT_PROFILE}},
            }
    elif path == "/api/residents/{resident_id}/apartments/{apartment_id}" and method == "DELETE":
        operation["description"] = (
            "Chỉ admin. Gỡ liên kết cư trú được xác nhận riêng, không sửa hợp đồng. "
            "Nếu hợp đồng với căn hộ vẫn hiệu lực, quyền truy cập theo hợp đồng vẫn còn. "
            "Gửi lại khi liên kết đã được gỡ vẫn trả hồ sơ hiện tại."
        )
        operation["responses"]["200"] = {
            "description": "Hồ sơ sau khi gỡ xác nhận",
            "content": {"application/json": {"schema": RESIDENT_PROFILE}},
        }
    elif path in ("/api/residents/me", "/api/residents/{resident_id}") and method == "GET":
        operation["description"] = (
            "Hồ sơ kèm apartment_ids/codes hợp nhất từ hợp đồng đang hiệu lực và xác nhận cư trú riêng. "
            "contract_apartment_ids là phạm vi hợp đồng; verified_apartment_ids và verified_apartments "
            "là phạm vi xác nhận riêng. registered_apartment_code không cấp quyền."
        )
        operation["responses"]["200"] = {
            "description": "Hồ sơ cư dân và phạm vi căn hộ",
            "content": {"application/json": {"schema": RESIDENT_PROFILE}},
        }
    elif path == "/api/residents" and method == "GET":
        operation["responses"]["200"] = {
            "description": "Danh sách hồ sơ kèm phạm vi căn hộ đã xác nhận",
            "content": {
                "application/json": {
                    "schema": object_schema({"items": {"type": "array", "items": RESIDENT_PROFILE}}, ("items",))
                }
            },
        }

    if path == "/api/billing/invoices/{kind}" and method == "POST":
        schemas = [object_schema(fields, ("apartment_id", "period", "due_date")) for fields in (MONTHLY, SEMIANNUAL)]
        request_body(operation, {}, (), {}, schema={"anyOf": schemas})
        content = operation["requestBody"]["content"]["application/json"]
        content.pop("example")
        content["examples"] = {
            "monthly": {
                "summary": "kind=monthly — lượng dùng × đơn giá",
                "value": {
                    "apartment_id": 1,
                    "period": "2026-10",
                    "electricity_usage": 100,
                    "electricity_unit_price": 3500,
                    "water_usage": 12,
                    "water_unit_price": 10000,
                    "due_date": "2026-11-10",
                },
            },
            "semiannual": {
                "summary": "kind=semiannual — dịch vụ/gửi xe",
                "value": {"apartment_id": 1, "period": "2026-H2", "service_fee": 3000000, "due_date": "2027-01-10"},
            },
        }
        operation["description"] = (
            "Admin hoặc kỹ thuật viên. Hóa đơn tháng: gửi đủ bốn trường lượng dùng/đơn giá; server tính từng khoản và làm tròn đến đồng (0,5 làm tròn lên). Nếu gửi tiền điện/nước/tổng phải khớp kết quả. API vẫn nhận phí trực tiếp cho dữ liệu cũ khi không gửi lượng dùng/đơn giá. Tổng phải > 0, một hóa đơn/căn hộ/kỳ. Bỏ parking_fee để tính phí gửi xe theo kỳ."
        )
        operation["responses"]["201"] = {"description": "Đã tạo hóa đơn với tổng tiền do server tính"}
    elif path == "/api/billing/invoices/{kind}/{invoice_id}" and method == "PATCH":
        fields = {
            key: value for key, value in {**MONTHLY, **SEMIANNUAL}.items() if key not in ("apartment_id", "period")
        }
        request_body(operation, fields, (), {"water_usage": 12.5, "due_date": "2026-11-15"})
        operation["description"] = (
            "Admin hoặc kỹ thuật viên; hóa đơn unpaid. Lượng dùng/đơn giá thay đổi được tính lại trên server. Hóa đơn đã phát hành QR không được sửa cách tính/số tiền, kể cả phiên hết hạn."
        )
    elif path.endswith("/pay") and path.startswith("/api/billing/invoices/"):
        request_body(
            operation,
            {
                "payment_method": choice("cash", "bank_transfer"),
                "transaction_code": string(maxLength=150),
                "amount": MONEY,
            },
            (),
            {"payment_method": "bank_transfer", "transaction_code": "BANK-2026-001"},
        )
        operation.setdefault("parameters", []).append(
            {
                "name": "Idempotency-Key",
                "in": "header",
                "required": False,
                "schema": string(maxLength=120),
                "description": "Gửi lại cùng khóa/nội dung để nhận cùng giao dịch, tránh thu trùng.",
            }
        )
        operation["description"] = (
            "Admin hoặc kỹ thuật viên; ghi nhận toàn bộ tiền mặt/chuyển khoản đã thực nhận, theo số tiền server lưu. Không ghi nhận thủ công khi có lệnh QR chờ."
        )
        operation["responses"]["201"] = {"description": "Đã ghi nhận thanh toán"}
    elif path.endswith("/checkout") and path.startswith("/api/billing/invoices/"):
        request_body(operation, {}, (), {})
        operation["description"] = (
            "Chỉ cư dân có quyền căn hộ. Một phiên chờ dùng chung cho hóa đơn; chỉ người giữ phiên "
            "nhận QR/nội dung chuyển khoản, thành viên khác xem trạng thái. Số tiền lấy từ server. "
            "Test dùng mô phỏng trên dashboard SePay; Live chuyển tiền thật."
        )
        operation["responses"]["200"] = {
            "description": "Dùng lại phiên đang chờ; thành viên khác không nhận QR",
            "content": {"application/json": {"schema": PAYMENT_ORDER}},
        }
        operation["responses"]["201"] = {
            "description": "Đã tạo phiên VietQR cho cư dân",
            "content": {"application/json": {"schema": PAYMENT_ORDER}},
        }
    elif path in ("/api/billing/orders/{order_id}/confirm-transfer", "/api/billing/orders/{order_id}/cancel"):
        request_body(operation, {}, (), {})
        operation["description"] = (
            "Chỉ cư dân đang giữ phiên pending. Báo đã chuyển chỉ đặt awaiting_confirmation, không ghi nhận tiền. "
            "Hủy chỉ khi chưa chuyển/nhận tiền; không cho hủy sau khi đã nhận một phần. "
            "Hết thời gian trên web không thu hồi được QR đã lưu."
        )
        operation["responses"]["200"] = {
            "description": "Trạng thái phiên sau thao tác",
            "content": {"application/json": {"schema": PAYMENT_ORDER}},
        }
    elif path == "/api/billing/orders/{order_id}/reconcile":
        request_body(operation, {}, (), {})
        operation["description"] = (
            "Admin, kỹ thuật viên hoặc cư dân thuộc căn hộ. Đọc giao dịch qua API SePay đúng môi trường khi có token "
            "và UUID tài khoản; nếu chưa có thì đọc trạng thái webhook đã lưu. Không tạo giao dịch/hoàn tiền."
        )
        operation["responses"]["200"] = {
            "description": "Trạng thái được server xác minh",
            "content": {"application/json": {"schema": PAYMENT_ORDER}},
        }
    elif path == "/api/billing/invoices/{kind}/{invoice_id}/release-payment":
        request_body(
            operation, {"note": string(minLength=1, maxLength=500)}, ("note",), {"note": "Sao kê không có khoản chuyển"}
        )
        operation["description"] = (
            "Admin hoặc kỹ thuật viên. Đóng phiên cư dân đã báo chuyển nhưng ngân hàng không ghi nhận tiền, sau khi đối soát SePay "
            "nếu có cấu hình. Giao dịch về sau vẫn được ghi nhận theo mã thanh toán."
        )
    elif path == "/api/billing/sepay/webhook":
        fields = {
            "id": {"oneOf": [ID, string(maxLength=100)]},
            "gateway": string(),
            "transactionDate": string(),
            "accountNumber": string(),
            "code": string(nullable=True),
            "content": string(),
            "transferType": choice("in", "out"),
            "transferAmount": number(minimum=1, maximum=1000000000),
            "referenceCode": string(maxLength=150),
            "subAccount": string(nullable=True),
        }
        request_body(
            operation,
            fields,
            ("id", "gateway", "accountNumber", "content", "transferType", "transferAmount"),
            {
                "id": 100001,
                "gateway": "Vietcombank",
                "transactionDate": "2026-11-06 12:00:00",
                "accountNumber": "TAI_KHOAN_TEST_CUA_BAN",
                "code": "QLCC012345ABCDEF",
                "content": "QLCC012345ABCDEF",
                "transferType": "in",
                "transferAmount": 10000,
                "referenceCode": "TEST-BANK-100001",
            },
        )
        operation["security"] = [{"SePayWebhookAuth": []}]
        operation["description"] = (
            "SePay gửi JSON, Authorization: Apikey <khóa webhook>. Không phải endpoint không xác thực. "
            "Kiểm tra ngân hàng/tài khoản, chiều tiền, mã tham chiếu và số tiền; chống webhook lặp. "
            "Chỉ phân bổ tối đa số còn nợ; phần dư/chưa xác định được lưu để BQL xử lý. Test/Live chọn tại server."
        )
        operation["responses"]["201"] = {
            "description": "Đã tiếp nhận, kể cả gửi lại cùng giao dịch",
            "content": {
                "application/json": {
                    "schema": object_schema({"success": {"type": "boolean", "enum": [True]}}, ("success",))
                }
            },
        }
    elif path == "/api/billing/sepay/transactions/{transaction_id}/resolve":
        request_body(
            operation,
            {"resolution": choice("refunded", "retained", "reviewed"), "note": string(minLength=1, maxLength=2000)},
            ("resolution", "note"),
            {"resolution": "reviewed", "note": "Đã kiểm tra tham chiếu, đang liên hệ cư dân."},
        )
        operation["description"] = (
            "Admin hoặc kỹ thuật viên. Ghi sổ xử lý và lịch sử thay đổi; không thực hiện chuyển tiền/hoàn tiền "
            "hoặc tự phân bổ tiền sang hóa đơn khác. Chỉ ghi refunded sau khi hoàn tiền thực tế."
        )
        operation["responses"]["200"] = {
            "description": "Giao dịch và ghi chú cập nhật",
            "content": {"application/json": {"schema": BANK_TRANSACTION}},
        }
    elif path == "/api/billing/overdue/run":
        request_body(operation, {}, (), {})

    if path == "/api/maintenance/tickets/{ticket_id}" and method == "PATCH":
        request_body(
            operation,
            {key: TICKET[key] for key in ("technician_id", "description", "priority", "status")},
            (),
            {"technician_id": 1, "status": "in_progress"},
        )
        operation["description"] = (
            "Admin phân công. Mọi kỹ thuật viên đều được gửi status cho mọi phiếu; người nhận phiếu chưa phân công sẽ thành người phụ trách. Luồng pending → in_progress → completed."
        )
    elif path == "/api/complaints" and method == "POST":
        request_body(
            operation,
            {
                "type": choice("complaint", "registration"),
                "category": string(),
                "content": string(maxLength=10000),
                "resident_id": {**ID, "description": "Không bắt buộc; cư dân không được tạo thay người khác."},
            },
            ("type", "content"),
            {"type": "registration", "category": "Gửi xe", "content": "Đăng ký xe máy biển 59A1-12345."},
        )
        operation["responses"]["201"] = {"description": "Đã nhận đơn"}
    elif path == "/api/complaints/{complaint_id}" and method == "PATCH":
        request_body(
            operation,
            {"status": choice("pending", "processing", "resolved", "rejected"), "response": string()},
            (),
            {"status": "resolved", "response": "Ban quản lý đã tiếp nhận và hoàn tất xử lý."},
        )
        operation["description"] = (
            "Chỉ admin; trạng thái resolved/rejected yêu cầu nội dung response. "
            "Mỗi phản hồi mới hoặc thay đổi được gửi riêng đến cư dân đã gửi đơn. "
            "Có thể sửa phản hồi đơn đã đóng, giữ nguyên trạng thái; gửi lại cùng nội dung không tạo thông báo trùng."
        )
    elif path == "/api/notifications/events":
        request_body(
            operation,
            {**NOTICE, "event_id": string(maxLength=200)},
            ("event_id", "type", "title", "content"),
            {
                "event_id": "billing:created:monthly:1",
                "type": "private",
                "target_apartment_id": 1,
                "title": "Hóa đơn mới",
                "content": "Kỳ 2026-10, hạn 2026-11-10.",
            },
        )
        operation["responses"]["201"] = {"description": "Đã nhận sự kiện; gửi lại cùng event_id trả 200"}
    elif path == "/api/notifications/push-tokens" and method in ("POST", "DELETE"):
        request_body(
            operation, {"token": string(maxLength=4096)}, ("token",), {"token": "<Firebase browser registration token>"}
        )
    elif path.endswith("/read") and path.startswith("/api/notifications/"):
        operation.pop("requestBody", None)
        operation["description"] = "Cư dân đánh dấu đã đọc thông báo thuộc phạm vi của mình. Không cần body."
    elif path == "/api/chatbot/ask":
        request_body(
            operation, {"question": string(maxLength=1500)}, ("question",), {"question": "Phòng camera ở đâu?"}
        )
        operation["description"] = (
            "Truy xuất FAQ và danh bạ do Ban quản lý quản lý, kèm sources và confidence. "
            "Chỉ nhận question; không nhận context hoặc quyền truy cập từ client. "
            "LLM tùy chọn diễn đạt lại nguồn; thiếu cấu hình hoặc lỗi trả về kiến thức gốc. "
            "engine là knowledge_base, llm hoặc resident_data. Tra cứu hóa đơn cá nhân "
            "cần bật cấu hình riêng và dùng JWT cư dân; dữ liệu này không gửi tới LLM."
        )

    if method == "GET":
        if path == "/api/billing/payment-config":
            config_schema = object_schema(
                {
                    "mode": choice("sepay"),
                    "environment": choice("test", "live"),
                    "ready": {"type": "boolean"},
                    "missing": {"type": "array", "items": string()},
                    "issues": {"type": "array", "items": string()},
                    "message": string(),
                    "reconciliation_enabled": {"type": "boolean"},
                }
            )
            operation["description"] = (
                "Cấu hình công khai đã bỏ khóa/token. ready=false khóa thanh toán; Test chỉ mô phỏng trên dashboard SePay."
            )
            operation["responses"]["200"] = {
                "description": "Trạng thái sẵn sàng thanh toán",
                "content": {"application/json": {"schema": config_schema}},
            }
        elif path == "/api/billing/orders/{order_id}":
            operation["description"] = (
                "Admin, kỹ thuật viên hoặc cư dân có quyền căn hộ. Chỉ người giữ phiên pending hợp lệ nhận QR và nội dung chuyển tiền; không lộ khóa provider."
            )
            operation["responses"]["200"] = {
                "description": "Trạng thái phiên và số tiền còn thiếu",
                "content": {"application/json": {"schema": PAYMENT_ORDER}},
            }
        elif path == "/api/billing/sepay/transactions":
            operation["description"] = (
                "Admin hoặc kỹ thuật viên. Tối đa 1000 giao dịch mới nhất, gồm phần đã phân bổ và tiền chưa phân bổ cần xử lý. Không phải API hoàn tiền."
            )
            operation["responses"]["200"] = {
                "description": "Sổ đối soát ngân hàng",
                "content": {
                    "application/json": {
                        "schema": object_schema({"items": {"type": "array", "items": BANK_TRANSACTION}}, ("items",))
                    }
                },
            }
        elif path == "/api/billing/invoices/{kind}":
            query(operation, "status", choice("unpaid", "paid", "overdue"))
            query(operation, "period", string(example="2026-10"), "YYYY-MM với monthly; YYYY-H1/H2 với semiannual.")
            query(operation, "apartment_id", ID)
        elif path == "/api/billing/payments":
            query(operation, "kind", choice("monthly", "semiannual"))
        elif path == "/api/billing/reports":
            query(operation, "year", number(minimum=2000, maximum=9999, example=2026))
            query(operation, "group", choice("month", "quarter"))
            operation["description"] = (
                "Chỉ admin. Tính theo kỳ hóa đơn (H1 vào tháng 1, H2 vào tháng 7): phát hành = đã thu + còn phải thu."
            )
        elif path in ("/api/parking/vehicles", "/api/parking/summary"):
            query(operation, "apartment_id", ID)
            if path.endswith("vehicles"):
                query(operation, "status", choice("active", "cancelled"))
            else:
                query(
                    operation,
                    "period",
                    string(pattern=r"^\d{4}-H[12]$"),
                    "Tùy chọn: báo giá kỳ 6 tháng, gồm recurring_fee, card_fee và parking_fee.",
                )
        elif path == "/api/parking/guest-daily":
            query(operation, "from", DATE)
            query(operation, "to", DATE)
        elif path == "/api/maintenance/tickets":
            query(operation, "status", choice("pending", "in_progress", "completed"))
        elif path == "/api/complaints":
            query(operation, "status", choice("pending", "processing", "resolved", "rejected"))
        elif path.endswith("/receipt"):
            operation["responses"]["200"] = {
                "description": "Tệp biên nhận HTML tải xuống, cần JWT",
                "content": {"text/html": {"schema": string()}},
            }
        elif path.endswith("/qr"):
            operation["description"] = (
                "Chỉ cư dân giữ phiên còn quyền chuyển khoản. PNG chứa số còn thiếu; Test không dùng ứng dụng ngân hàng thật. Phiên hết hạn không thu hồi QR đã lưu."
            )
            operation["responses"]["200"] = {
                "description": "Ảnh VietQR, cần JWT đúng người giữ phiên",
                "content": {"image/png": {"schema": string(format="binary")}},
            }
    return operation
