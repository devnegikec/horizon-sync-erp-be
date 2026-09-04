import json
import random

import requests
from qr_helpers import login

# API Configuration
URL = "http://localhost:8001/api/v1/qr-products"

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
    "Origin": "http://localhost:4200",
}

# Base catalog items to seed sample generation
PRODUCT_BASE_NAMES = [
    "Prestige Dura Cast Iron Cookware Dosa Tawa",
    "Prestige Tri-Ply Stainless Steel Kadhai 26cm",
    "Prestige Hard Anodised Non-Stick Fry Pan",
    "Prestige Deluxe Alpha Outer Lid Pressure Cooker 3L",
    "Prestige Omega Select Plus Flat Base Appam Patra",
    "Prestige Royale Plus Induction Base Gas Stove 3 Burner",
    "Prestige Svachh Clip-On Stainless Steel Cooker 5L",
    "Prestige Iris 750 Watt Mixer Grinder 4 Jars",
    "Prestige Multi-Cooker Kettle 1.2L",
    "Prestige Electric Induction Cooktop PIC 20.0",
]


def generate_sample_products(count=10):
    products = []
    for i in range(count):
        # Generate dynamic SKUs and GTINs to ensure uniqueness
        sku = f"PTK-DUK-M{str(i + 1).zfill(3)}"
        gtin = f"123124{random.randint(1000000, 9999999)}"

        payload = {
            "name": PRODUCT_BASE_NAMES[i % len(PRODUCT_BASE_NAMES)],
            "sku": sku,
            "packaging_details": {
                "unit_name": "Each",
                "conversion_factor": 1,
                "length_mm": random.randint(100, 300),
                "width_mm": random.randint(100, 300),
                "height_mm": random.randint(100, 400),
                "weight_grams": random.randint(200, 1500),
            },
            "brand_id": "45d2f323-cf95-423b-b6f9-3564ccc497d6",
            "gtin": gtin,
            "industry": "Home Appliances",
            "landing_page": "https://www.bajajelectricals.com",
            "client_product_auth_url": "https://www.bajajelectricals.com/products/pygmy-mini-110-mm-personal-fan",
            "activation_method": "pre",
            "sr_number_type": "R6DAN",
            "serial_prefix_setting_id": "dbc02524-fa85-41cb-b223-6688a712fc6c",
            "shelf_life_setting_id": "8fe5f480-5e71-43f4-80b7-3db45950c27d",
            "email": None,
            "phone_number": None,
            "redirect_to_client": False,
        }
        products.append(payload)
    return products


def create_products():
    token = login()
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    sample_products = generate_sample_products(10)

    for index, product in enumerate(sample_products, 1):
        try:
            response = requests.post(
                URL, headers=headers, data=json.dumps(product), timeout=30
            )

            if response.status_code in (200, 201):
                print(
                    f"[{index}/10] Success: Created '{product['name']}' (SKU: {product['sku']})"
                )
            else:
                print(f"[{index}/10] Failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"[{index}/10] Error connecting to server: {str(e)}")


if __name__ == "__main__":
    create_products()
