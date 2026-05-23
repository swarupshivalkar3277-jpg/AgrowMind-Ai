from __future__ import annotations

from datetime import datetime, timezone

from bson.errors import InvalidId
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from auth.deps import require_role
from auth.models import user_public
from database.mongodb import db
from routes.marketplace import ORDER_STATUSES, ProductIn, object_id, serialize_order, serialize_product


router = APIRouter(prefix="/admin", tags=["Admin"])


class BlockUserIn(BaseModel):
    blocked: bool = True


class RoleUpdateIn(BaseModel):
    role: str = Field(pattern="^(farmer|admin)$")


@router.get("/users")
async def list_users(search: str = "", user=Depends(require_role("admin"))):
    query = {}
    if search:
        query = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]
        }
    cursor = db.users.find(query).sort("created_at", -1).limit(300)
    return {"success": True, "data": {"items": [user_public(item) | {"blocked": bool(item.get("blocked", False))} async for item in cursor]}}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user=Depends(require_role("admin"))):
    try:
        target_id = ObjectId(user_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    if str(user["_id"]) == str(target_id):
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")

    result = await db.users.delete_one({"_id": target_id})
    if result.deleted_count != 1:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": {"deleted": True}}


@router.patch("/users/{user_id}/block")
async def block_user(user_id: str, payload: BlockUserIn, user=Depends(require_role("admin"))):
    target_id = object_id(user_id)
    if str(user["_id"]) == str(target_id):
        raise HTTPException(status_code=400, detail="You cannot block your own admin account")

    updated = await db.users.find_one_and_update(
        {"_id": target_id},
        {"$set": {"blocked": payload.blocked, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": {"user": user_public(updated) | {"blocked": bool(updated.get("blocked", False))}}}


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, payload: RoleUpdateIn, user=Depends(require_role("admin"))):
    updated = await db.users.find_one_and_update(
        {"_id": object_id(user_id)},
        {"$set": {"role": payload.role, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "data": {"user": user_public(updated)}}


@router.get("/orders")
async def admin_orders(
    status_value: str = "",
    search: str = "",
    user=Depends(require_role("admin")),
):
    query = {}
    if status_value:
        if status_value not in ORDER_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid order status")
        query["order_status"] = status_value
    if search:
        query["$or"] = [
            {"transaction_id": {"$regex": search, "$options": "i"}},
            {"user_email": {"$regex": search, "$options": "i"}},
        ]
    cursor = db.orders.find(query).sort("created_at", -1).limit(300)
    return {"success": True, "data": {"items": [serialize_order(order) async for order in cursor]}}


@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status_value: str = Query(...), user=Depends(require_role("admin"))):
    if status_value not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid order status")

    now = datetime.now(timezone.utc)
    order = await db.orders.find_one_and_update(
        {"_id": object_id(order_id)},
        {
            "$set": {"order_status": status_value, "updated_at": now},
            "$push": {"tracking": {"status": status_value, "message": f"Order marked {status_value}", "at": now}},
        },
        return_document=ReturnDocument.AFTER,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"success": True, "data": {"order": serialize_order(order)}}


@router.get("/analytics")
async def analytics(user=Depends(require_role("admin"))):
    total_users = await db.users.count_documents({})
    total_farmers = await db.users.count_documents({"role": "farmer"})
    total_orders = await db.orders.count_documents({})
    pending_orders = await db.orders.count_documents({"order_status": "pending"})
    low_stock_products = await db.products.count_documents({"stock": {"$lte": 5}})
    total_ai_predictions = await db.prediction_history.count_documents({})
    revenue_rows = db.orders.aggregate([
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ])
    revenue_doc = await revenue_rows.to_list(length=1)
    revenue = float(revenue_doc[0]["total"]) if revenue_doc else 0.0

    disease_rows = await db.prediction_history.aggregate([
        {"$group": {"_id": "$prediction.disease", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 6},
    ]).to_list(length=6)
    crop_rows = await db.prediction_history.aggregate([
        {"$group": {"_id": "$crop", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 6},
    ]).to_list(length=6)

    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "total_farmers": total_farmers,
            "total_orders": total_orders,
            "total_revenue": revenue,
            "pending_orders": pending_orders,
            "low_stock_products": low_stock_products,
            "total_ai_predictions": total_ai_predictions,
            "top_diseases": [{"name": row["_id"] or "unknown", "count": row["count"]} for row in disease_rows],
            "top_crops": [{"name": row["_id"] or "unknown", "count": row["count"]} for row in crop_rows],
        },
    }


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_admin_product(payload: ProductIn, user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    document = {
        **payload.model_dump(),
        "seller_id": str(user["_id"]),
        "seller_name": user.get("name", user.get("email", "AgroMind Admin")),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.products.insert_one(document)
    product = await db.products.find_one({"_id": result.inserted_id})
    return {"success": True, "data": {"product": serialize_product(product)}}


@router.put("/products/{product_id}")
async def update_admin_product(product_id: str, payload: ProductIn, user=Depends(require_role("admin"))):
    product = await db.products.find_one_and_update(
        {"_id": object_id(product_id)},
        {"$set": {**payload.model_dump(), "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "data": {"product": serialize_product(product)}}


@router.delete("/products/{product_id}")
async def delete_admin_product(product_id: str, user=Depends(require_role("admin"))):
    result = await db.products.delete_one({"_id": object_id(product_id)})
    if result.deleted_count != 1:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "data": {"deleted": True}}
