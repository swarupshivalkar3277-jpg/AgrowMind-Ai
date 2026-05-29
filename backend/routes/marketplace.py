from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import base64
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from auth.deps import get_current_user, require_role
from database.mongodb import db, drop_parallel_array_product_indexes
from utils.rate_limit import rate_limit

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
logger = logging.getLogger("agromind.marketplace")

TAX_RATE = 0.05
FREE_SHIPPING_THRESHOLD = 999
DELIVERY_CHARGE = 60
ORDER_STATUSES = {"pending", "paid", "processing", "shipped", "delivered", "cancelled", "refund_requested", "refunded"}
ORDER_STATUS_FLOW = [
    "ORDER_PLACED",
    "PAYMENT_PENDING",
    "PAYMENT_SUCCESS",
    "PROCESSING",
    "PACKED",
    "SHIPPED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
    "REFUND_REQUESTED",
    "REFUNDED",
]
ORDER_STATUSES = set(ORDER_STATUS_FLOW) | ORDER_STATUSES
REFUNDABLE_STATUSES = {"paid", "processing", "shipped", "delivered"}
REFUNDABLE_STATUSES |= {"PAYMENT_SUCCESS", "PROCESSING", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED"}
MAX_CLOUDINARY_IMAGE_BYTES = max(512 * 1024, int(os.getenv("CLOUDINARY_MAX_IMAGE_BYTES", str(8 * 1024 * 1024))))
CLOUDINARY_UPLOAD_TIMEOUT_SECONDS = float(os.getenv("CLOUDINARY_UPLOAD_TIMEOUT_SECONDS", "25"))
CLOUDINARY_MAX_GALLERY_IMAGES = max(0, int(os.getenv("CLOUDINARY_MAX_GALLERY_IMAGES", "6")))
LEGACY_STATUS_MAP = {
    "pending": "ORDER_PLACED",
    "paid": "PAYMENT_SUCCESS",
    "processing": "PROCESSING",
    "shipped": "SHIPPED",
    "delivered": "DELIVERED",
    "cancelled": "CANCELLED",
    "refund_requested": "REFUND_REQUESTED",
    "refunded": "REFUNDED",
}


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=99)


class CheckoutAddress(BaseModel):
    full_name: str
    mobile: str
    address: str
    state: str
    district: str
    pin_code: str
    location_lat: float | None = None
    location_lng: float | None = None
    location_label: str | None = None
    payment_method: str = Field(default="cash_on_delivery")
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None


class RazorpayOrderRequest(CheckoutAddress):
    receipt: str | None = None


class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class ProductIn(BaseModel):
    name: str
    category: str
    crop_type: list[str] = []
    disease_tags: list[str] = []
    brand: str = ""
    manufacturer: str = ""
    mrp: float = Field(default=0, ge=0)
    discount: float = Field(default=0, ge=0)
    price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    sold_quantity: int = Field(default=0, ge=0)
    unit: str = Field(default="piece", max_length=40)
    unit_size: str = Field(default="1 piece", max_length=80)
    sku: str = ""
    image: str = ""
    gallery: list[str] = []
    short_description: str = ""
    description: str = ""
    benefits: list[str] = []
    usage_instructions: str = ""
    precautions: str = ""
    tags: list[str] = []
    featured: bool = False
    status: str = Field(default="active", pattern="^(active|draft|archived)$")
    rating: float = Field(default=4.0, ge=0, le=5)


def normalize_status(status_value: str | None) -> str:
    if not status_value:
        return "ORDER_PLACED"
    return LEGACY_STATUS_MAP.get(status_value, status_value)


def stock_available(product: dict) -> int:
    stock_quantity = int(product.get("stock_quantity", product.get("stock", 0)) or 0)
    reserved_quantity = int(product.get("reserved_quantity", 0) or 0)
    return max(0, stock_quantity - reserved_quantity)


def normalize_product_document(document: dict) -> dict:
    stock_quantity = document.get("stock_quantity")
    if stock_quantity is None:
        stock_quantity = document.get("stock", 0)
    document["stock_quantity"] = int(stock_quantity or 0)
    document["reserved_quantity"] = int(document.get("reserved_quantity", 0) or 0)
    document["sold_quantity"] = int(document.get("sold_quantity", 0) or 0)
    document["stock"] = stock_available(document)
    return document


def cloudinary_configured() -> bool:
    return all(os.getenv(name) for name in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))


async def upload_data_url_to_cloudinary(value: str, folder: str = "agromind/products") -> str:
    if not value or not value.startswith("data:image/"):
        return value
    if not cloudinary_configured():
        raise HTTPException(status_code=503, detail="Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET.")

    match = re.match(r"data:(image/[\w.+-]+);base64,(.+)", value, re.DOTALL)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid image data URL")
    try:
        decoded = base64.b64decode(match.group(2), validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image") from exc
    if len(decoded) > MAX_CLOUDINARY_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Product image is too large")

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    timestamp = int(datetime.now(timezone.utc).timestamp())
    public_id = uuid4().hex
    signature_payload = f"folder={folder}&public_id={public_id}&timestamp={timestamp}{api_secret}"
    signature = hashlib.sha1(signature_payload.encode()).hexdigest()
    files = {"file": ("product.jpg", decoded, match.group(1))}
    data = {
        "api_key": api_key,
        "timestamp": str(timestamp),
        "folder": folder,
        "public_id": public_id,
        "signature": signature,
    }
    try:
        timeout = httpx.Timeout(CLOUDINARY_UPLOAD_TIMEOUT_SECONDS, connect=8.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload", data=data, files=files)
    except httpx.RequestError as exc:
        logger.exception("Cloudinary upload failed before response")
        raise HTTPException(status_code=502, detail="Cloudinary upload failed") from exc
    if response.status_code >= 400:
        logger.error("Cloudinary upload failed status=%s body=%s", response.status_code, response.text[:500])
        raise HTTPException(status_code=502, detail="Cloudinary upload failed")
    url = response.json().get("secure_url")
    if not url:
        raise HTTPException(status_code=502, detail="Cloudinary did not return a secure URL")
    logger.info("Cloudinary upload success public_id=%s", public_id)
    return url


async def prepare_product_payload(payload: ProductIn) -> dict:
    document = payload.model_dump()
    document["image"] = await upload_data_url_to_cloudinary(document.get("image", ""))
    gallery = [item for item in document.get("gallery", []) if item][:CLOUDINARY_MAX_GALLERY_IMAGES]
    document["gallery"] = await asyncio.gather(
        *(upload_data_url_to_cloudinary(item) for item in gallery)
    )
    return normalize_product_document(document)


def object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc


def serialize_product(product: dict) -> dict:
    product = normalize_product_document(dict(product))
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "category": product.get("category"),
        "crop_type": product.get("crop_type", []),
        "disease_tags": product.get("disease_tags", []),
        "brand": product.get("brand", ""),
        "manufacturer": product.get("manufacturer", ""),
        "mrp": float(product.get("mrp", product.get("price", 0)) or 0),
        "discount": float(product.get("discount", 0) or 0),
        "price": float(product.get("price", 0)),
        "stock": int(product.get("stock", 0)),
        "stock_quantity": int(product.get("stock_quantity", 0)),
        "reserved_quantity": int(product.get("reserved_quantity", 0)),
        "sold_quantity": int(product.get("sold_quantity", 0)),
        "unit": product.get("unit", "piece"),
        "unit_size": product.get("unit_size", "1 piece"),
        "sku": product.get("sku", ""),
        "image": product.get("image", ""),
        "gallery": product.get("gallery", []),
        "short_description": product.get("short_description", ""),
        "description": product.get("description", ""),
        "benefits": product.get("benefits", []),
        "usage_instructions": product.get("usage_instructions", ""),
        "precautions": product.get("precautions", ""),
        "tags": product.get("tags", []),
        "featured": bool(product.get("featured", False)),
        "status": product.get("status", "active"),
        "rating": float(product.get("rating", 0)),
        "seller_id": product.get("seller_id"),
        "seller_name": product.get("seller_name", "AgroMind Store"),
    }


def serialize_order(order: dict) -> dict:
    status_value = normalize_status(order.get("order_status"))
    return {
        "id": str(order["_id"]),
        "items": order.get("items", []),
        "address": order.get("address", {}),
        "subtotal": order.get("subtotal", 0),
        "tax": order.get("tax", 0),
        "shipping": order.get("shipping", 0),
        "total": order.get("total", 0),
        "payment_method": order.get("payment_method"),
        "payment_status": order.get("payment_status"),
        "order_status": status_value,
        "tracking": order.get("status_history", order.get("tracking", [])),
        "status_history": order.get("status_history", order.get("tracking", [])),
        "refund_status": order.get("refund_status", "none"),
        "refund_requested_at": order.get("refund_requested_at"),
        "refunded_at": order.get("refunded_at"),
        "transaction_id": order.get("transaction_id"),
        "created_at": order.get("created_at"),
    }


async def cleanup_seed_products() -> None:
    await drop_parallel_array_product_indexes()
    await db.products.delete_many({"seller_id": "system"})


async def recommended_products(crop: str, disease: str, limit: int = 6) -> list[dict]:
    query = {
        "$or": [
            {"crop_type": crop},
            {"disease_tags": disease},
            {"name": {"$regex": disease.replace("_", " "), "$options": "i"}},
        ]
    }
    cursor = db.products.find(query).sort([("rating", -1), ("stock", -1)]).limit(limit)
    return [serialize_product(product) async for product in cursor]


async def ensure_stock(cart: dict) -> None:
    for item in cart["items"]:
        product = await db.products.find_one({"_id": object_id(item["product"]["id"])})
        if not product or stock_available(product) < int(item["quantity"]):
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {item['product']['name']}")


async def decrement_stock_atomic(cart: dict) -> None:
    updated: list[tuple[ObjectId, int]] = []
    for item in cart["items"]:
        product_id = object_id(item["product"]["id"])
        quantity = int(item["quantity"])
        await db.products.update_one(
            {"_id": product_id, "stock_quantity": {"$exists": False}},
            [{"$set": {
                "stock_quantity": {"$ifNull": ["$stock", 0]},
                "reserved_quantity": {"$ifNull": ["$reserved_quantity", 0]},
                "sold_quantity": {"$ifNull": ["$sold_quantity", 0]},
            }}],
        )
        product = await db.products.find_one_and_update(
            {
                "_id": product_id,
                "$expr": {"$gte": [{"$subtract": [{"$ifNull": ["$stock_quantity", "$stock"]}, {"$ifNull": ["$reserved_quantity", 0]}]}, quantity]},
            },
            {
                "$inc": {"stock_quantity": -quantity, "stock": -quantity, "sold_quantity": quantity},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if product:
            updated.append((product_id, quantity))
            await log_inventory_change(product_id, -quantity, "sale", {"product_name": item["product"]["name"]})
            continue

        for rollback_id, rollback_quantity in updated:
            await db.products.update_one({"_id": rollback_id}, {"$inc": {"stock_quantity": rollback_quantity, "stock": rollback_quantity, "sold_quantity": -rollback_quantity}})
        raise HTTPException(status_code=409, detail=f"Insufficient stock for {item['product']['name']}")


async def log_inventory_change(product_id: ObjectId, quantity_delta: int, reason: str, metadata: dict | None = None) -> None:
    await db.inventory_logs.insert_one({
        "product_id": str(product_id),
        "quantity_delta": quantity_delta,
        "reason": reason,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc),
    })


async def restore_stock(cart_or_order: dict) -> None:
    for item in cart_or_order.get("items", []):
        product_id = item.get("product", {}).get("id")
        if not product_id:
            continue
        await db.products.update_one(
            {"_id": object_id(product_id)},
            {
                "$inc": {"stock_quantity": int(item.get("quantity", 0)), "stock": int(item.get("quantity", 0)), "sold_quantity": -int(item.get("quantity", 0))},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        await log_inventory_change(object_id(product_id), int(item.get("quantity", 0)), "restore", {"order_id": str(cart_or_order.get("_id", ""))})


async def record_status_history(order_id: ObjectId, status_value: str, message: str, actor: str = "system") -> dict:
    entry = {"order_id": str(order_id), "status": status_value, "message": message, "actor": actor, "at": datetime.now(timezone.utc)}
    await db.status_history.insert_one(entry)
    return {key: value for key, value in entry.items() if key != "order_id"}


def razorpay_credentials() -> tuple[str, str]:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not configured")
    return key_id, key_secret


async def cart_document(user_id: str) -> dict:
    cart = await db.carts.find_one({"user_id": user_id})
    if cart:
        return cart

    now = datetime.now(timezone.utc)
    cart = {"user_id": user_id, "items": [], "created_at": now, "updated_at": now}
    result = await db.carts.insert_one(cart)
    cart["_id"] = result.inserted_id
    return cart


async def hydrate_cart(cart: dict) -> dict:
    product_ids = [object_id(item["product_id"]) for item in cart.get("items", [])]
    products = {}
    if product_ids:
        async for product in db.products.find({"_id": {"$in": product_ids}}):
            products[str(product["_id"])] = serialize_product(product)

    items = []
    cleaned_items = []
    subtotal = 0.0
    for item in cart.get("items", []):
        product = products.get(item["product_id"])
        if not product or product["stock"] <= 0:
            continue
        quantity = min(int(item.get("quantity", 1)), product["stock"])
        if quantity <= 0:
            continue
        line_total = round(product["price"] * quantity, 2)
        subtotal += line_total
        cleaned_items.append({"product_id": item["product_id"], "quantity": quantity})
        items.append({"product": product, "quantity": quantity, "line_total": line_total})

    if cleaned_items != cart.get("items", []):
        await db.carts.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": cleaned_items, "updated_at": datetime.now(timezone.utc)}},
        )

    subtotal = round(subtotal, 2)
    tax = round(subtotal * TAX_RATE, 2)
    shipping = 0 if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD else DELIVERY_CHARGE
    total = round(subtotal + tax + shipping, 2)

    return {
        "id": str(cart["_id"]),
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "count": sum(item["quantity"] for item in items),
    }


def verify_razorpay_signature(payload: CheckoutAddress | RazorpayVerifyRequest) -> bool:
    secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not secret or not payload.razorpay_order_id or not payload.razorpay_payment_id or not payload.razorpay_signature:
        return False

    message = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode()
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, payload.razorpay_signature)


@router.get("/products")
async def list_products(
    search: str = "",
    category: str = "",
    crop: str = "",
    disease: str = "",
    limit: int = Query(default=60, ge=1, le=100),
):
    filters = []

    if search:
        filters.append({"$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]})
    if category:
        filters.append({"category": category})
    if crop:
        filters.append({"crop_type": crop})
    if disease:
        filters.append({"disease_tags": disease})

    query = {"$and": filters} if filters else {}
    cursor = db.products.find(query).sort([("rating", -1), ("name", 1)]).limit(limit)
    return {"success": True, "items": [serialize_product(product) async for product in cursor]}


@router.get("/products/{product_id}")
async def product_details(product_id: str):
    product = await db.products.find_one({"_id": object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": serialize_product(product)}


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductIn, user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    document = {
        **await prepare_product_payload(payload),
        "seller_id": str(user["_id"]),
        "seller_name": user.get("name", user.get("email", "Seller")),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.products.insert_one(document)
    product = await db.products.find_one({"_id": result.inserted_id})
    return {"success": True, "product": serialize_product(product)}


@router.put("/products/{product_id}")
async def update_product(product_id: str, payload: ProductIn, user=Depends(require_role("admin"))):
    existing = await db.products.find_one({"_id": object_id(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    product = await db.products.find_one_and_update(
        {"_id": object_id(product_id)},
        {"$set": {**await prepare_product_payload(payload), "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": serialize_product(product)}


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(require_role("admin"))):
    existing = await db.products.find_one({"_id": object_id(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    result = await db.products.delete_one({"_id": object_id(product_id)})
    return {"success": result.deleted_count == 1}


@router.get("/cart")
async def get_cart(user=Depends(get_current_user)):
    cart = await cart_document(str(user["_id"]))
    return {"success": True, "cart": await hydrate_cart(cart)}


@router.post("/cart/items")
async def add_cart_item(payload: CartItemIn, user=Depends(get_current_user)):
    product = await db.products.find_one({"_id": object_id(payload.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if stock_available(product) < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    cart = await cart_document(str(user["_id"]))
    items = cart.get("items", [])
    for item in items:
        if item["product_id"] == payload.product_id:
            item["quantity"] = min(99, item["quantity"] + payload.quantity)
            break
    else:
        items.append(payload.model_dump())

    await db.carts.update_one({"_id": cart["_id"]}, {"$set": {"items": items, "updated_at": datetime.now(timezone.utc)}})
    return await get_cart(user)


@router.put("/cart/items/{product_id}")
async def update_cart_item(product_id: str, payload: CartItemIn, user=Depends(get_current_user)):
    cart = await cart_document(str(user["_id"]))
    items = [
        {"product_id": item["product_id"], "quantity": payload.quantity if item["product_id"] == product_id else item["quantity"]}
        for item in cart.get("items", [])
    ]
    await db.carts.update_one({"_id": cart["_id"]}, {"$set": {"items": items, "updated_at": datetime.now(timezone.utc)}})
    return await get_cart(user)


@router.delete("/cart/items/{product_id}")
async def remove_cart_item(product_id: str, user=Depends(get_current_user)):
    cart = await cart_document(str(user["_id"]))
    items = [item for item in cart.get("items", []) if item["product_id"] != product_id]
    await db.carts.update_one({"_id": cart["_id"]}, {"$set": {"items": items, "updated_at": datetime.now(timezone.utc)}})
    return await get_cart(user)


@router.post("/wishlist/{product_id}")
async def toggle_wishlist(product_id: str, user=Depends(get_current_user)):
    product = await db.products.find_one({"_id": object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = {"user_id": str(user["_id"]), "product_id": product_id}
    existing = await db.wishlist.find_one(query)
    if existing:
        await db.wishlist.delete_one(query)
        return {"success": True, "wishlisted": False}

    await db.wishlist.insert_one({**query, "created_at": datetime.now(timezone.utc)})
    return {"success": True, "wishlisted": True}


@router.post("/payment/razorpay-order", dependencies=[Depends(rate_limit(10, 300))])
async def create_razorpay_order(payload: RazorpayOrderRequest, user=Depends(get_current_user)):
    if user.get("role") != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can place marketplace orders")

    cart = await hydrate_cart(await cart_document(str(user["_id"])))
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")
    await ensure_stock(cart)

    key_id, key_secret = razorpay_credentials()
    receipt = payload.receipt or f"agromind-{uuid4().hex[:16]}"
    amount_paise = int(round(cart["total"] * 100))
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/orders",
                auth=(key_id, key_secret),
                json={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": {"user_id": str(user["_id"]), "email": user["email"]},
                },
            )
    except httpx.RequestError as exc:
        logger.exception("Razorpay order request failed user=%s amount_paise=%s", user.get("email"), amount_paise)
        raise HTTPException(status_code=502, detail="Razorpay is unreachable from the backend. Check Render network and Razorpay configuration.") from exc

    if response.status_code >= 400:
        logger.error(
            "Razorpay order creation failed status=%s user=%s amount_paise=%s body=%s",
            response.status_code,
            user.get("email"),
            amount_paise,
            response.text[:1000],
        )
        message = "Razorpay order creation failed"
        try:
            error_body = response.json()
            message = error_body.get("error", {}).get("description") or message
        except ValueError:
            pass
        raise HTTPException(status_code=502, detail=message)

    order = response.json()
    await db.payments.insert_one({
        "user_id": str(user["_id"]),
        "user_email": user["email"],
        "status": "created",
        "method": "razorpay",
        "razorpay_order_id": order.get("id"),
        "amount_paise": amount_paise,
        "amount": cart["total"],
        "currency": order.get("currency", "INR"),
        "cart_snapshot": cart,
        "address": payload.model_dump(exclude={"receipt", "payment_method", "razorpay_order_id", "razorpay_payment_id", "razorpay_signature"}),
        "created_at": datetime.now(timezone.utc),
    })
    return {
        "success": True,
        "data": {
            "razorpay_order_id": order.get("id"),
            "amount": amount_paise,
            "currency": order.get("currency", "INR"),
            "razorpay_key": key_id,
            "cart": cart,
        },
        "key_id": key_id,
        "razorpay_order": order,
        "cart": cart,
    }


@router.post("/payment/verify", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit(15, 300))])
async def verify_razorpay_payment(payload: RazorpayVerifyRequest, user=Depends(get_current_user)):
    if user.get("role") != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can place marketplace orders")

    if not verify_razorpay_signature(payload):
        await db.payments.update_one(
            {"razorpay_order_id": payload.razorpay_order_id, "user_id": str(user["_id"])},
            {"$set": {"status": "failed", "failure_reason": "invalid_signature", "updated_at": datetime.now(timezone.utc)}},
        )
        raise HTTPException(status_code=400, detail="Payment verification failed")

    payment = await db.payments.find_one({
        "razorpay_order_id": payload.razorpay_order_id,
        "user_id": str(user["_id"]),
        "method": "razorpay",
    })
    if not payment:
        raise HTTPException(status_code=404, detail="Payment session not found")
    if payment.get("status") == "paid" and payment.get("order_id"):
        order = await db.orders.find_one({"_id": object_id(payment["order_id"])})
        return {"success": True, "data": {"order": serialize_order(order), "payment": {"status": "paid"}}}
    if payment.get("status") not in {"created", "failed"}:
        raise HTTPException(status_code=409, detail="Payment verification is already being processed")

    claimed = await db.payments.find_one_and_update(
        {"_id": payment["_id"], "status": {"$in": ["created", "failed"]}},
        {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        raise HTTPException(status_code=409, detail="Payment verification is already being processed")
    payment = claimed

    cart = payment.get("cart_snapshot") or {}
    if not cart.get("items"):
        raise HTTPException(status_code=400, detail="Payment cart snapshot is empty")

    try:
        await ensure_stock(cart)
        await decrement_stock_atomic(cart)
    except HTTPException:
        await db.payments.update_one(
            {"_id": payment["_id"]},
            {"$set": {"status": "stock_failed", "updated_at": datetime.now(timezone.utc)}},
        )
        raise

    now = datetime.now(timezone.utc)
    order = {
        "user_id": str(user["_id"]),
        "user_email": user["email"],
        "items": cart["items"],
        "address": payment.get("address", {}),
        "subtotal": cart["subtotal"],
        "tax": cart["tax"],
        "shipping": cart["shipping"],
        "total": cart["total"],
        "payment_method": "razorpay",
        "payment_status": "paid",
        "order_status": "PAYMENT_SUCCESS",
        "tracking": [{"status": "PAYMENT_SUCCESS", "message": "Payment verified and order received", "at": now}],
        "status_history": [{"status": "PAYMENT_SUCCESS", "message": "Payment verified and order received", "actor": "system", "at": now}],
        "transaction_id": payload.razorpay_payment_id,
        "razorpay_order_id": payload.razorpay_order_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.orders.insert_one(order)
    await record_status_history(result.inserted_id, "PAYMENT_SUCCESS", "Payment verified and order received")
    await db.payments.update_one(
        {"_id": payment["_id"], "status": {"$ne": "paid"}},
        {
            "$set": {
                "order_id": str(result.inserted_id),
                "payment_id": payload.razorpay_payment_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
                "status": "paid",
                "updated_at": now,
            }
        },
    )
    await db.carts.update_one({"user_id": str(user["_id"])}, {"$set": {"items": [], "updated_at": now}})

    created = await db.orders.find_one({"_id": result.inserted_id})
    return {
        "success": True,
        "data": {
            "order": serialize_order(created),
            "payment": {
                "payment_id": payload.razorpay_payment_id,
                "order_id": str(result.inserted_id),
                "razorpay_order_id": payload.razorpay_order_id,
                "amount": cart["total"],
                "status": "paid",
            },
        },
        "order": serialize_order(created),
    }


@router.get("/wishlist")
async def get_wishlist(user=Depends(get_current_user)):
    ids = [object_id(item["product_id"]) async for item in db.wishlist.find({"user_id": str(user["_id"])})]
    cursor = db.products.find({"_id": {"$in": ids}}) if ids else []
    items = [serialize_product(product) async for product in cursor] if ids else []
    return {"success": True, "items": items}


@router.post("/checkout", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit(10, 300))])
async def checkout(payload: CheckoutAddress, user=Depends(get_current_user)):
    if user.get("role") != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can place marketplace orders")

    cart = await hydrate_cart(await cart_document(str(user["_id"])))
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")

    payment_method = payload.payment_method
    payment_status = "pending"
    transaction_id = None

    if payment_method == "cash_on_delivery":
        payment_status = "pending"
        transaction_id = f"COD-{uuid4().hex[:10].upper()}"
    elif payment_method == "razorpay":
        raise HTTPException(status_code=400, detail="Use /marketplace/payment/verify for Razorpay payments")
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

    await decrement_stock_atomic(cart)
    now = datetime.now(timezone.utc)
    order_status = "PAYMENT_SUCCESS" if payment_status == "paid" else "PAYMENT_PENDING"
    tracking_message = "Order placed with Cash on Delivery" if payment_method == "cash_on_delivery" else "Order received"
    order = {
        "user_id": str(user["_id"]),
        "user_email": user["email"],
        "items": cart["items"],
        "address": payload.model_dump(exclude={"razorpay_order_id", "razorpay_payment_id", "razorpay_signature"}),
        "subtotal": cart["subtotal"],
        "tax": cart["tax"],
        "shipping": cart["shipping"],
        "total": cart["total"],
        "payment_method": payment_method,
        "payment_status": payment_status,
        "order_status": order_status,
        "tracking": [{"status": order_status, "message": tracking_message, "at": now}],
        "status_history": [{"status": order_status, "message": tracking_message, "actor": "system", "at": now}],
        "transaction_id": transaction_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.orders.insert_one(order)
    await record_status_history(result.inserted_id, order_status, tracking_message)
    await db.payments.insert_one({
        "user_id": str(user["_id"]),
        "order_id": str(result.inserted_id),
        "status": payment_status,
        "method": payment_method,
        "transaction_id": transaction_id,
        "amount": cart["total"],
        "created_at": now,
    })
    await db.carts.update_one({"user_id": str(user["_id"])}, {"$set": {"items": [], "updated_at": now}})

    created = await db.orders.find_one({"_id": result.inserted_id})
    return {"success": True, "order": serialize_order(created)}


@router.get("/orders")
async def my_orders(user=Depends(get_current_user)):
    cursor = db.orders.find({"user_id": str(user["_id"])}).sort("created_at", -1)
    return {"success": True, "items": [serialize_order(order) async for order in cursor]}


@router.get("/orders/{order_id}")
async def order_details(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": object_id(order_id), "user_id": str(user["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"success": True, "order": serialize_order(order)}


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": object_id(order_id), "user_id": str(user["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if normalize_status(order.get("order_status")) in {"SHIPPED", "DELIVERED", "REFUND_REQUESTED", "REFUNDED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Order can no longer be cancelled")

    now = datetime.now(timezone.utc)
    await restore_stock(order)
    status_entry = await record_status_history(order["_id"], "CANCELLED", "Cancelled by user. Stock restored.", "customer")
    updated = await db.orders.find_one_and_update(
        {"_id": object_id(order_id)},
        {
            "$set": {
                "order_status": "CANCELLED",
                "payment_status": "cancelled" if order.get("payment_method") == "cash_on_delivery" else order.get("payment_status", "paid"),
                "updated_at": now,
            },
            "$push": {"tracking": {"status": "CANCELLED", "message": "Cancelled by user. Stock restored.", "at": now}, "status_history": status_entry},
        },
        return_document=ReturnDocument.AFTER,
    )
    return {"success": True, "order": serialize_order(updated)}


@router.post("/orders/{order_id}/refund")
async def request_refund(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": object_id(order_id), "user_id": str(user["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("payment_method") != "razorpay" or order.get("payment_status") != "paid":
        raise HTTPException(status_code=400, detail="Refund is available only for paid Razorpay orders")
    if normalize_status(order.get("order_status")) not in REFUNDABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Order is not eligible for refund")

    now = datetime.now(timezone.utc)
    status_entry = await record_status_history(order["_id"], "REFUND_REQUESTED", "Refund requested. Admin will process manually.", "customer")
    updated = await db.orders.find_one_and_update(
        {"_id": order["_id"]},
        {
            "$set": {
                "order_status": "REFUND_REQUESTED",
                "refund_status": "requested",
                "refund_requested_at": now,
                "updated_at": now,
            },
            "$push": {"tracking": {"status": "REFUND_REQUESTED", "message": "Refund requested. Admin will process manually.", "at": now}, "status_history": status_entry},
        },
        return_document=ReturnDocument.AFTER,
    )
    return {"success": True, "order": serialize_order(updated)}
