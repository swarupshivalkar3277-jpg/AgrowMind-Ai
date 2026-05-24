from __future__ import annotations

import hashlib
import hmac
import logging
import os
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
REFUNDABLE_STATUSES = {"paid", "processing", "shipped", "delivered"}


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


def object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc


def serialize_product(product: dict) -> dict:
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
        "order_status": order.get("order_status"),
        "tracking": order.get("tracking", []),
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
    await cleanup_seed_products()
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
        if not product or int(product.get("stock", 0)) < int(item["quantity"]):
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {item['product']['name']}")


async def decrement_stock_atomic(cart: dict) -> None:
    updated: list[tuple[ObjectId, int]] = []
    for item in cart["items"]:
        product_id = object_id(item["product"]["id"])
        quantity = int(item["quantity"])
        product = await db.products.find_one_and_update(
            {"_id": product_id, "stock": {"$gte": quantity}},
            {"$inc": {"stock": -quantity}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if product:
            updated.append((product_id, quantity))
            continue

        for rollback_id, rollback_quantity in updated:
            await db.products.update_one({"_id": rollback_id}, {"$inc": {"stock": rollback_quantity}})
        raise HTTPException(status_code=409, detail=f"Insufficient stock for {item['product']['name']}")


async def restore_stock(cart_or_order: dict) -> None:
    for item in cart_or_order.get("items", []):
        product_id = item.get("product", {}).get("id")
        if not product_id:
            continue
        await db.products.update_one(
            {"_id": object_id(product_id)},
            {"$inc": {"stock": int(item.get("quantity", 0))}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        )


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
    await cleanup_seed_products()
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
        **payload.model_dump(),
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
        {"$set": {**payload.model_dump(), "updated_at": datetime.now(timezone.utc)}},
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
    if product.get("stock", 0) < payload.quantity:
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
        "order_status": "paid",
        "tracking": [{"status": "paid", "message": "Payment verified and order received", "at": now}],
        "transaction_id": payload.razorpay_payment_id,
        "razorpay_order_id": payload.razorpay_order_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.orders.insert_one(order)
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
    order_status = "paid" if payment_status == "paid" else "pending"
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
        "transaction_id": transaction_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.orders.insert_one(order)
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
    if order.get("order_status") in {"shipped", "delivered", "refund_requested", "refunded", "cancelled"}:
        raise HTTPException(status_code=400, detail="Order can no longer be cancelled")

    now = datetime.now(timezone.utc)
    await restore_stock(order)
    updated = await db.orders.find_one_and_update(
        {"_id": object_id(order_id)},
        {
            "$set": {
                "order_status": "cancelled",
                "payment_status": "cancelled" if order.get("payment_method") == "cash_on_delivery" else order.get("payment_status", "paid"),
                "updated_at": now,
            },
            "$push": {"tracking": {"status": "cancelled", "message": "Cancelled by user. Stock restored.", "at": now}},
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
    if order.get("order_status") not in REFUNDABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Order is not eligible for refund")

    now = datetime.now(timezone.utc)
    updated = await db.orders.find_one_and_update(
        {"_id": order["_id"]},
        {
            "$set": {
                "order_status": "refund_requested",
                "refund_status": "requested",
                "refund_requested_at": now,
                "updated_at": now,
            },
            "$push": {"tracking": {"status": "refund_requested", "message": "Refund requested. Admin will process manually.", "at": now}},
        },
        return_document=ReturnDocument.AFTER,
    )
    return {"success": True, "order": serialize_order(updated)}
