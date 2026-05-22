from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import requests
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from auth.deps import get_current_user, require_role
from database.mongodb import db, drop_parallel_array_product_indexes

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])

TAX_RATE = 0.05
FREE_SHIPPING_THRESHOLD = 999
DELIVERY_CHARGE = 60


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
    payment_method: str = Field(default="cash_on_delivery")
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None


class RazorpayOrderRequest(BaseModel):
    receipt: str | None = None


class ProductIn(BaseModel):
    name: str
    category: str
    crop_type: list[str] = []
    disease_tags: list[str] = []
    price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    image: str = ""
    description: str = ""
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
        "price": float(product.get("price", 0)),
        "stock": int(product.get("stock", 0)),
        "image": product.get("image", ""),
        "description": product.get("description", ""),
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


async def decrement_stock(cart: dict) -> None:
    await ensure_stock(cart)
    for item in cart["items"]:
        await db.products.update_one(
            {"_id": object_id(item["product"]["id"])},
            {"$inc": {"stock": -int(item["quantity"])}},
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
    subtotal = 0.0
    for item in cart.get("items", []):
        product = products.get(item["product_id"])
        if not product:
            continue
        quantity = int(item.get("quantity", 1))
        line_total = round(product["price"] * quantity, 2)
        subtotal += line_total
        items.append({"product": product, "quantity": quantity, "line_total": line_total})

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


def verify_razorpay_signature(payload: CheckoutAddress) -> bool:
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
async def create_product(payload: ProductIn, user=Depends(require_role("admin", "farmer", "seller"))):
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
async def update_product(product_id: str, payload: ProductIn, user=Depends(require_role("admin", "farmer", "seller"))):
    existing = await db.products.find_one({"_id": object_id(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    if user.get("role") != "admin" and existing.get("seller_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="You can edit only your own products")

    product = await db.products.find_one_and_update(
        {"_id": object_id(product_id)},
        {"$set": {**payload.model_dump(), "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": serialize_product(product)}


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(require_role("admin", "farmer", "seller"))):
    existing = await db.products.find_one({"_id": object_id(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    if user.get("role") != "admin" and existing.get("seller_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="You can delete only your own products")

    result = await db.products.delete_one({"_id": object_id(product_id)})
    return {"success": result.deleted_count == 1}


@router.get("/seller/products")
async def seller_products(user=Depends(require_role("admin", "farmer", "seller"))):
    query = {} if user.get("role") == "admin" else {"seller_id": str(user["_id"])}
    cursor = db.products.find(query).sort("created_at", -1)
    return {"success": True, "items": [serialize_product(product) async for product in cursor]}


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


@router.post("/payment/razorpay-order")
async def create_razorpay_order(payload: RazorpayOrderRequest, user=Depends(get_current_user)):
    cart = await hydrate_cart(await cart_document(str(user["_id"])))
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")
    await ensure_stock(cart)

    key_id, key_secret = razorpay_credentials()
    receipt = payload.receipt or f"agromind-{uuid4().hex[:16]}"
    response = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(key_id, key_secret),
        json={
            "amount": int(round(cart["total"] * 100)),
            "currency": "INR",
            "receipt": receipt,
            "notes": {"user_id": str(user["_id"]), "email": user["email"]},
        },
        timeout=20,
    )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Razorpay order creation failed: {response.text}")

    order = response.json()
    await db.payments.insert_one({
        "user_id": str(user["_id"]),
        "status": "created",
        "method": "razorpay",
        "razorpay_order_id": order.get("id"),
        "amount": cart["total"],
        "created_at": datetime.now(timezone.utc),
    })
    return {"success": True, "key_id": key_id, "razorpay_order": order, "cart": cart}


@router.get("/wishlist")
async def get_wishlist(user=Depends(get_current_user)):
    ids = [object_id(item["product_id"]) async for item in db.wishlist.find({"user_id": str(user["_id"])})]
    cursor = db.products.find({"_id": {"$in": ids}}) if ids else []
    items = [serialize_product(product) async for product in cursor] if ids else []
    return {"success": True, "items": items}


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(payload: CheckoutAddress, user=Depends(get_current_user)):
    cart = await hydrate_cart(await cart_document(str(user["_id"])))
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")

    payment_method = payload.payment_method
    payment_status = "pending"
    transaction_id = None

    if payment_method == "cash_on_delivery":
        payment_status = "pending"
        transaction_id = f"COD-{uuid4().hex[:10].upper()}"
    elif payment_method in {"upi", "card"}:
        payment_status = "paid"
        transaction_id = f"SIM-{uuid4().hex[:12].upper()}"
    elif payment_method == "razorpay":
        if not verify_razorpay_signature(payload):
            await db.payments.insert_one({
                "user_id": str(user["_id"]),
                "status": "failed",
                "method": payment_method,
                "created_at": datetime.now(timezone.utc),
            })
            raise HTTPException(status_code=400, detail="Payment verification failed")
        payment_status = "paid"
        transaction_id = payload.razorpay_payment_id
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

    await decrement_stock(cart)
    now = datetime.now(timezone.utc)
    order = {
        "user_id": str(user["_id"]),
        "items": cart["items"],
        "address": payload.model_dump(exclude={"razorpay_order_id", "razorpay_payment_id", "razorpay_signature"}),
        "subtotal": cart["subtotal"],
        "tax": cart["tax"],
        "shipping": cart["shipping"],
        "total": cart["total"],
        "payment_method": payment_method,
        "payment_status": payment_status,
        "order_status": "confirmed",
        "tracking": [{"status": "confirmed", "message": "Order received", "at": now}],
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


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"_id": object_id(order_id), "user_id": str(user["_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("order_status") in {"shipped", "delivered"}:
        raise HTTPException(status_code=400, detail="Order can no longer be cancelled")

    now = datetime.now(timezone.utc)
    updated = await db.orders.find_one_and_update(
        {"_id": object_id(order_id)},
        {"$set": {"order_status": "cancelled", "updated_at": now}, "$push": {"tracking": {"status": "cancelled", "message": "Cancelled by user", "at": now}}},
        return_document=ReturnDocument.AFTER,
    )
    return {"success": True, "order": serialize_order(updated)}


@router.get("/admin/orders")
async def admin_orders(user=Depends(require_role("admin"))):
    cursor = db.orders.find({}).sort("created_at", -1).limit(200)
    return {"success": True, "items": [serialize_order(order) async for order in cursor]}


@router.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status_value: str, user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    order = await db.orders.find_one_and_update(
        {"_id": object_id(order_id)},
        {"$set": {"order_status": status_value, "updated_at": now}, "$push": {"tracking": {"status": status_value, "message": f"Order marked {status_value}", "at": now}}},
        return_document=ReturnDocument.AFTER,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"success": True, "order": serialize_order(order)}
