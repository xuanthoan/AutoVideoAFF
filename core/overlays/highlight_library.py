"""Smart sales highlight styles and CTA wording presets."""
from __future__ import annotations

import random

from core.overlays.template_manager import TextTemplate


HIGHLIGHT_STYLE_NAMES = [
    "TikTok Bold", "Flash Sale", "Premium Luxury", "Neon Glow", "Urgent CTA", "Shopee Style",
    "TikTok Shop", "Modern Minimal", "Bubble Cute", "Strong Black Yellow", "Hot Deal Red", "Luxury Gold",
    "Clean White", "Black Friday", "Summer Sale", "Mega Discount", "Viral Trend", "Elegant Beauty",
    "Cosmetic Pink", "Kitchen Home", "Food Delivery", "Gaming Neon", "Fashion Streetwear", "Minimal Premium",
    "Random Style",
]

HIGHLIGHT_ANIMATIONS = [
    "None", "Pop", "Bounce", "Pulse", "Wiggle", "Zoom In", "Zoom Out", "Float", "Slide Up", "Slide Down",
    "Shake", "Fade In", "Fade Out", "Scale Up", "Scale Down", "Rotate Float", "Random Animation",
]

SALES_WORDING_LIBRARY = {
    "fashion": [
        "HOT TREND", "MẶC CỰC ĐẸP", "FORM SIÊU XỊN", "ĐANG HOT", "OUTFIT ĐỈNH", "BEST SELLER",
        "CỰC TÔN DÁNG", "MIX DỄ", "CHẤT VẢI CAO CẤP", "CHUẨN HOT GIRL", "FREESHIP", "GIÁ QUÁ HỜI",
        "MUA NGAY", "SIÊU TÔN DÁNG", "ĐANG GIẢM GIÁ", "LOOK SANG XỊN",
    ],
    "beauty": [
        "DA CĂNG BÓNG", "TRẮNG SÁNG", "CỰC MỊN", "DÙNG LÀ MÊ", "HOT TREND", "REVIEW RẤT TỐT",
        "CỰC KỲ ĐÁNG TIỀN", "MÙI THƠM DỄ CHỊU", "SP CHÍNH HÃNG", "BÁN CHẠY", "DA KHỎE HƠN",
        "MAKEUP SIÊU ĐẸP", "CỰC KỲ TỰ NHIÊN", "ĐƯỢC REVIEW SIÊU TỐT", "GIÁ QUÁ TỐT", "MUA NGAY",
    ],
    "home": [
        "SIÊU TIỆN", "RẤT DỄ DÙNG", "NHÀ NÀO CŨNG CẦN", "QUÁ THÔNG MINH", "TIẾT KIỆM THỜI GIAN",
        "DÙNG RẤT THÍCH", "CỰC KỲ TIỆN LỢI", "GIÁ TỐT", "BỀN ĐẸP", "HOẠT ĐỘNG ÊM", "SIÊU NHỎ GỌN",
        "CỰC KÌ ĐÁNG MUA", "CHẤT LƯỢNG CAO", "RẤT ỔN ÁP", "MUA LÀ DÙNG NGAY", "GỌN GÀNG",
        "SIÊU TIẾT KIỆM", "CỰC KỲ HỮU ÍCH", "BEST SELLER", "BÁN CHẠY",
    ],
    "food": [
        "SIÊU NGON", "ĂN LÀ GHIỀN", "QUÁ CUỐN", "HOT TREND", "ĐẬM VỊ", "CỰC NGON", "ĂN SIÊU ĐÃ",
        "NGON KHÓ CƯỠNG", "BÁN CHẠY", "GIÁ QUÁ TỐT", "COMBO SIÊU HỜI", "KHUYẾN MÃI LỚN", "DEAL NGON",
        "QUÁ CHẤT LƯỢNG", "ĂN LÀ MÊ", "MUA NGAY", "SIÊU HẤP DẪN", "RẤT ĐÁNG THỬ",
        "SIÊU NHIỀU TOPPING", "ĐANG GIẢM GIÁ",
    ],
}


class HighlightStyleManager:
    RANDOM_STYLE_NAME = "Random Style"
    BUILT_INS = [
        TextTemplate("TikTok Bold", "#FFFFFF", "#111111", "#FF2D55", "black@0.45", ("#FFFFFF", "#111111")),
        TextTemplate("Flash Sale", "#FFFFFF", "#FF2D2D", "#FFD400", "#FFD400@0.55", ("#FFFFFF", "#FF2D2D")),
        TextTemplate("Premium Luxury", "#F8E7B0", "#17110A", "#D7B35A", "black@0.40", ("#F8E7B0", "#17110A")),
        TextTemplate("Neon Glow", "#B9FFFC", "#111227", "#00FFF0", "#00FFF0@0.55", ("#B9FFFC", "#111227")),
        TextTemplate("Urgent CTA", "#FFFFFF", "#F01515", "#FFFFFF", "black@0.40", ("#FFFFFF", "#F01515")),
        TextTemplate("Shopee Style", "#FFFFFF", "#EE4D2D", "#FFD15C", "black@0.35", ("#FFFFFF", "#EE4D2D")),
        TextTemplate("TikTok Shop", "#FFFFFF", "#00A6FF", "#FF2D55", "black@0.30", ("#FFFFFF", "#00A6FF")),
        TextTemplate("Modern Minimal", "#111111", "#F5F5F5", "#111111", "black@0.18", ("#111111", "#F5F5F5")),
        TextTemplate("Bubble Cute", "#FF4FA3", "#FFE1F0", "#FFFFFF", "#FF4FA3@0.28", ("#FF4FA3", "#FFE1F0")),
        TextTemplate("Strong Black Yellow", "#111111", "#FFD400", "#111111", "black@0.24", ("#111111", "#FFD400")),
        TextTemplate("Hot Deal Red", "#FFFFFF", "#D9001B", "#FFD400", "black@0.42", ("#FFFFFF", "#D9001B")),
        TextTemplate("Luxury Gold", "#3A2600", "#F7C948", "#FFFFFF", "black@0.25", ("#3A2600", "#F7C948")),
        TextTemplate("Clean White", "#111111", "#FFFFFF", "#DDDDDD", "black@0.18", ("#111111", "#FFFFFF")),
        TextTemplate("Black Friday", "#FFE600", "#000000", "#FFE600", "black@0.50", ("#FFE600", "#000000")),
        TextTemplate("Summer Sale", "#FFFFFF", "#FF8A00", "#00C2FF", "black@0.26", ("#FFFFFF", "#FF8A00")),
        TextTemplate("Mega Discount", "#FFFFFF", "#7B2DFF", "#FFD400", "black@0.35", ("#FFFFFF", "#7B2DFF")),
        TextTemplate("Viral Trend", "#FFFFFF", "#FF2D55", "#00F2EA", "black@0.35", ("#FFFFFF", "#FF2D55")),
        TextTemplate("Elegant Beauty", "#FFFFFF", "#B45A7A", "#F5D6E3", "black@0.22", ("#FFFFFF", "#B45A7A")),
        TextTemplate("Cosmetic Pink", "#FFFFFF", "#FF66B3", "#FFFFFF", "black@0.25", ("#FFFFFF", "#FF66B3")),
        TextTemplate("Kitchen Home", "#FFFFFF", "#2E7D32", "#C8E6C9", "black@0.25", ("#FFFFFF", "#2E7D32")),
        TextTemplate("Food Delivery", "#FFFFFF", "#FF6B00", "#FFE066", "black@0.30", ("#FFFFFF", "#FF6B00")),
        TextTemplate("Gaming Neon", "#D7FF00", "#1B103A", "#00E5FF", "#00E5FF@0.50", ("#D7FF00", "#1B103A")),
        TextTemplate("Fashion Streetwear", "#FFFFFF", "#222222", "#F0F0F0", "black@0.38", ("#FFFFFF", "#222222")),
        TextTemplate("Minimal Premium", "#E8D8B0", "#232323", "#E8D8B0", "black@0.28", ("#E8D8B0", "#232323")),
    ]

    def names(self) -> list[str]:
        return [template.name for template in self.BUILT_INS] + [self.RANDOM_STYLE_NAME]

    def get(self, name: str) -> TextTemplate:
        if name == self.RANDOM_STYLE_NAME:
            return self.random_style()
        return next((template for template in self.BUILT_INS if template.name == name), self.BUILT_INS[0])

    def random_style(self) -> TextTemplate:
        return random.choice(self.BUILT_INS)

    def random_wording(self, category: str | None = None) -> str:
        values = SALES_WORDING_LIBRARY.get(category or "", [])
        if not values:
            values = [word for words in SALES_WORDING_LIBRARY.values() for word in words]
        return random.choice(values)
