import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# 로컬에선 .env를 읽고, Railway에선 Variables가 이미 들어 있음
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
FRONT_ORIGINS = [
    o.strip().rstrip("/")  # 끝의 "/" 는 CORS 에서 불일치를 일으키므로 제거
    for o in os.getenv("FRONT_ORIGINS", "").split(",")
    if o.strip()
]

sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

app = FastAPI(title="my-api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONT_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlaceIn(BaseModel):
    name: str
    description: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/v")
def health():
    return {"s": "100", "t":"200"}


@app.get("/health/db")
def health_db():
    """Supabase 연결 + places 테이블 존재 확인"""
    try:
        sb.table("places").select("id").limit(1).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"supabase error: {e}")
    return {"status": "ok", "db": "connected"}


@app.get("/places")
def list_places():
    try:
        res = sb.table("places").select("*").order("id", desc=True).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return res.data


@app.post("/places", status_code=201)
def create_place(place: PlaceIn):
    try:
        res = sb.table("places").insert(place.model_dump()).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return res.data[0]


@app.delete("/places/{place_id}")
def delete_place(place_id: int):
    try:
        sb.table("places").delete().eq("id", place_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"deleted": place_id}


# ───────────────────────── 쇼핑몰 / 장바구니 ─────────────────────────
# 로그인 없이 브라우저가 만든 cart_id(랜덤 문자열)로 장바구니를 구분한다.
CartId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{8,64}$")]


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class QuantityIn(BaseModel):
    quantity: int = Field(ge=0, le=99)  # 0 이면 삭제


def load_cart(cart_id: str) -> dict:
    """장바구니 내용 + 합계를 계산해서 돌려준다."""
    rows = (
        sb.table("cart_items")
        .select("product_id, quantity, product:products(*)")
        .eq("cart_id", cart_id)
        .order("id")
        .execute()
        .data
    )
    items = [
        {**r, "subtotal": r["quantity"] * r["product"]["price"]} for r in rows
    ]
    return {
        "cart_id": cart_id,
        "items": items,
        "count": sum(i["quantity"] for i in items),
        "total": sum(i["subtotal"] for i in items),
    }


@app.get("/products")
def list_products():
    try:
        return sb.table("products").select("*").order("id").execute().data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cart/{cart_id}")
def get_cart(cart_id: CartId):
    try:
        return load_cart(cart_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cart/{cart_id}/items")
def add_to_cart(cart_id: CartId, body: CartItemIn):
    """담기: 이미 담긴 상품이면 수량만 늘린다."""
    try:
        product = (
            sb.table("products").select("id").eq("id", body.product_id).execute().data
        )
        if not product:
            raise HTTPException(status_code=404, detail="상품이 없습니다")
        found = (
            sb.table("cart_items")
            .select("quantity")
            .eq("cart_id", cart_id)
            .eq("product_id", body.product_id)
            .execute()
            .data
        )
        if found:
            qty = min(99, found[0]["quantity"] + body.quantity)
            sb.table("cart_items").update({"quantity": qty}).eq(
                "cart_id", cart_id
            ).eq("product_id", body.product_id).execute()
        else:
            sb.table("cart_items").insert(
                {
                    "cart_id": cart_id,
                    "product_id": body.product_id,
                    "quantity": body.quantity,
                }
            ).execute()
        return load_cart(cart_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/cart/{cart_id}/items/{product_id}")
def set_quantity(cart_id: CartId, product_id: int, body: QuantityIn):
    """수량 변경 (0 이면 삭제)"""
    try:
        t = sb.table("cart_items")
        if body.quantity == 0:
            t.delete().eq("cart_id", cart_id).eq("product_id", product_id).execute()
        else:
            res = (
                t.update({"quantity": body.quantity})
                .eq("cart_id", cart_id)
                .eq("product_id", product_id)
                .execute()
            )
            if not res.data:
                raise HTTPException(status_code=404, detail="장바구니에 없는 상품입니다")
        return load_cart(cart_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cart/{cart_id}/items/{product_id}")
def remove_from_cart(cart_id: CartId, product_id: int):
    try:
        sb.table("cart_items").delete().eq("cart_id", cart_id).eq(
            "product_id", product_id
        ).execute()
        return load_cart(cart_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cart/{cart_id}")
def clear_cart(cart_id: CartId):
    try:
        sb.table("cart_items").delete().eq("cart_id", cart_id).execute()
        return load_cart(cart_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
