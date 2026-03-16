from fastapi import FastAPI, Query, status, Response, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI(title="FastAPI Internship Training - Consolidated")

# Initial product catalog
products = [
    {"id": 1, "name": "Wireless Mouse", "price": 499, "category": "Electronics", "in_stock": True},
    {"id": 2, "name": "Notebook", "price": 99, "category": "Stationery", "in_stock": True},
    {"id": 3, "name": "USB Hub", "price": 799, "category": "Electronics", "in_stock": False},
    {"id": 4, "name": "Pen Set", "price": 49, "category": "Stationery", "in_stock": True},
    {"id": 5, "name": "Laptop Stand", "price": 1299, "category": "Electronics", "in_stock": True},
    {"id": 6, "name": "Mechanical Keyboard", "price": 2499, "category": "Electronics", "in_stock": True},
    {"id": 7, "name": "Webcam", "price": 1899, "category": "Electronics", "in_stock": False},
]

# In-memory database lists
feedback = []
orders = []
order_counter = 1

# Assignment 4 (Day 5): Cart memory
cart = [] 


# ==========================================
# 🛡️ PYDANTIC MODELS
# ==========================================

class NewProduct(BaseModel):
    name: str
    price: int
    category: str
    in_stock: bool = True

class CustomerFeedback(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=300)

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=50)

class BulkOrder(BaseModel):
    company_name: str = Field(..., min_length=2)
    contact_email: str = Field(..., min_length=5)
    items: List[OrderItem] = Field(..., min_items=1)

class SingleOrder(BaseModel):
    product_id: int
    quantity: int

# Assignment 4 (Day 5): Checkout Model
class CheckoutRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    delivery_address: str = Field(..., min_length=10)


# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def find_product(product_id: int):
    """Search products list by ID. Returns product dict or None."""
    return next((p for p in products if p['id'] == product_id), None)

def calculate_total(product: dict, quantity: int) -> int:
    """Multiply price by quantity and return total."""
    return product['price'] * quantity


# ==========================================
# 🚀 ENDPOINTS - STATIC / FIXED ROUTES
# ==========================================

# Retrieve the complete list of products
@app.get("/products")
def get_all_products():
    return {"products": products, "total": len(products)}

# Get inventory audit summary
@app.get('/products/audit')
def product_audit():
    in_stock_list  = [p for p in products if p['in_stock']]
    out_stock_list = [p for p in products if not p['in_stock']]
    stock_value    = sum(p['price'] * 10 for p in in_stock_list)
    priciest       = max(products, key=lambda p: p['price'])
    return {
        'total_products':    len(products),
        'in_stock_count':    len(in_stock_list),
        'out_of_stock_names': [p['name'] for p in out_stock_list],
        'total_stock_value':  stock_value,
        'most_expensive':    {'name': priciest['name'], 'price': priciest['price']},
    }

# Apply a category-wide discount
@app.put('/products/discount')
def bulk_discount(
    category: str = Query(..., description='Category to discount'),
    discount_percent: int = Query(..., ge=1, le=99, description='% off'),
):
    updated = []
    for p in products:
        if p['category'] == category:
            p['price'] = int(p['price'] * (1 - discount_percent / 100))
            updated.append(p)
    if not updated:
        return {'message': f'No products found in category: {category}'}
    return {
        'message':          f'{discount_percent}% discount applied to {category}',
        'updated_count':    len(updated),
        'updated_products': updated,
    }

# Retrieve all in-stock products
@app.get("/products/instock")
def get_instock():
    available = [p for p in products if p["in_stock"] == True]
    return {"in_stock_products": available, "count": len(available)}

# Retrieve the cheapest and most expensive products
@app.get("/products/deals")
def get_deals():
    cheapest  = min(products, key=lambda p: p["price"])
    expensive = max(products, key=lambda p: p["price"])
    return {
        "best_deal": cheapest,
        "premium_pick": expensive,
    }

# Retrieve an overview summary of the product catalog
@app.get("/products/summary")
def product_summary():
    in_stock   = [p for p in products if p["in_stock"]]
    out_stock  = [p for p in products if not p["in_stock"]]
    expensive  = max(products, key=lambda p: p["price"])
    cheapest   = min(products, key=lambda p: p["price"])
    categories = list(set(p["category"] for p in products))
    return {
        "total_products":     len(products),
        "in_stock_count":     len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive":     {"name": expensive["name"], "price": expensive["price"]},
        "cheapest":           {"name": cheapest["name"],  "price": cheapest["price"]},
        "categories":         categories,
    }

# Filter products based on category, minimum price, and maximum price
@app.get("/products/filter")
def filter_products(
    category: Optional[str] = Query(None, description="Category filter"),
    max_price: Optional[int] = Query(None, description="Maximum price"),
    min_price: Optional[int] = Query(None, description='Minimum price')
):
    result = products
    if category:
        result = [p for p in result if p['category'].lower() == category.lower()]
    if max_price:
        result = [p for p in result if p['price'] <= max_price]
    if min_price:
        result = [p for p in result if p['price'] >= min_price]
    return {"results": result, "total": len(result)}


# ==========================================
# 🛒 CART SYSTEM ENDPOINTS (Assignment 4 / Day 5)
# ==========================================

# Assignment 4: View the current cart
@app.get('/cart')
def view_cart():
    if not cart:
        return {'message': 'Cart is empty', 'items': [], 'grand_total': 0}
    grand_total = sum(item['subtotal'] for item in cart)
    return {
        'items':       cart,
        'item_count':  len(cart),
        'grand_total': grand_total,
    }

# Assignment 4: Add items to the cart, handling duplicates and out-of-stock items
@app.post('/cart/add')
def add_to_cart(
    product_id: int = Query(..., description='Product ID to add'),
    quantity:   int = Query(1,   description='How many (default 1)'),
):
    product = find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product['in_stock']:
        raise HTTPException(status_code=400, detail=f"{product['name']} is out of stock")
        
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
        
    # Check if item is already in cart to update quantity
    for item in cart:
        if item['product_id'] == product_id:
            item['quantity'] += quantity
            item['subtotal']  = calculate_total(product, item['quantity'])
            return {'message': 'Cart updated', 'cart_item': item}
            
    # Add new item to cart
    cart_item = {
        'product_id':   product_id,
        'product_name': product['name'],
        'quantity':     quantity,
        'unit_price':   product['price'],
        'subtotal':     calculate_total(product, quantity),
    }
    cart.append(cart_item)
    return {'message': 'Added to cart', 'cart_item': cart_item}

# Assignment 4: Process checkout and empty the cart
@app.post('/cart/checkout', status_code=status.HTTP_201_CREATED)
def checkout(checkout_data: CheckoutRequest):
    global order_counter
    
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")
        
    placed_orders = []
    grand_total   = 0
    
    for item in cart:
        order = {
            'order_id':         order_counter,
            'customer_name':    checkout_data.customer_name,
            'product':          item['product_name'],
            'quantity':         item['quantity'],
            'delivery_address': checkout_data.delivery_address,
            'total_price':      item['subtotal'],
            'status':           'confirmed',
        }
        orders.append(order)
        placed_orders.append(order)
        grand_total   += item['subtotal']
        order_counter += 1
        
    cart.clear() # Empty the cart after successful checkout
    
    return {
        'message':       'Checkout successful',
        'orders_placed': placed_orders,
        'grand_total':   grand_total,
    }


# ==========================================
# 🔍 ENDPOINTS - SEARCH, CATEGORY & DYNAMIC IDs
# ==========================================

# Retrieve products by their assigned category
@app.get("/products/category/{category_name}")
def get_by_category(category_name: str):
    result = [p for p in products if p["category"].lower() == category_name.lower()]
    if not result:
        return {"error": "No products found in this category"}
    return {"category": category_name, "products": result, "total": len(result)}

# Search for products matching a specific keyword in their name
@app.get("/products/search/{keyword}")
def search_products(keyword: str):
    results = [p for p in products if keyword.lower() in p["name"].lower()]
    if not results:
        return {"message": "No products matched your search"}
    return {"keyword": keyword, "results": results, "total_matches": len(results)}

# Fetch only the name and price data for a specific product ID
@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    product = find_product(product_id)
    if product:
        return {"name": product["name"], "price": product["price"]}
    return {"error": "Product not found"}

# Add a new product via POST
@app.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(product: NewProduct, response: Response):
    if any(p['name'].lower() == product.name.lower() for p in products):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Product with this name already exists"}
    
    next_id = max((p['id'] for p in products), default=0) + 1
    new_product = {
        "id": next_id,
        "name": product.name,
        "price": product.price,
        "category": product.category,
        "in_stock": product.in_stock
    }
    products.append(new_product)
    return {"message": "Product added", "product": new_product}

# Retrieve full details for a single product
@app.get('/products/{product_id}')
def get_single_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {"error": "Product not found"}
    return product

# Update price or stock status for an existing product
@app.put('/products/{product_id}')
def update_product(product_id: int, in_stock: Optional[bool] = None, price: Optional[int] = None, response: Response = Response()):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "Product not found"}
        
    if in_stock is not None:
        product['in_stock'] = in_stock
    if price is not None:
        product['price'] = price
    return product

# Delete an existing product
@app.delete('/products/{product_id}')
def delete_product_endpoint(product_id: int, response: Response):
    product = find_product(product_id)
    if not product:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'error': 'Product not found'}
    products.remove(product)
    return {'message': f"Product '{product['name']}' deleted"}

# Assignment 4: Remove a specific item from the cart
@app.delete('/cart/{product_id}')
def remove_from_cart(product_id: int):
    for item in cart:
        if item['product_id'] == product_id:
            cart.remove(item)
            return {'message': f"{item['product_name']} removed from cart"}
            
    raise HTTPException(status_code=404, detail="Product not in cart")


# ==========================================
# 🏪 ENDPOINTS - STORE, ORDERS & FEEDBACK
# ==========================================

# Retrieve store-wide statistics and data
@app.get("/store/summary")
def store_summary():
    in_stock_count  = len([p for p in products if p["in_stock"]])
    out_stock_count = len(products) - in_stock_count
    categories      = list(set([p["category"] for p in products]))
    return {
        "store_name":     "My E-commerce Store",
        "total_products": len(products),
        "in_stock":       in_stock_count,
        "out_of_stock":   out_stock_count,
        "categories":     categories,
    }

# Submit customer feedback and store it in memory
@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.model_dump())
    return {
        "message":        "Feedback submitted successfully",
        "feedback":       data.model_dump(),
        "total_feedback": len(feedback),
    }

# Process a bulk order containing multiple items, verifying stock per item
@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    confirmed, failed, grand_total = [], [], 0
    for item in order.items:
        product = find_product(item.product_id)
        if not product:
            failed.append({"product_id": item.product_id, "reason": "Product not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": f"{product['name']} is out of stock"})
        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})
    return {"company": order.company_name, "confirmed": confirmed,
            "failed": failed, "grand_total": grand_total}

# Create a single order and set its initial status to pending
@app.post("/orders")
def create_single_order(order: SingleOrder):
    global order_counter
    new_order = {
        "order_id": order_counter,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "status": "pending" 
    }
    orders.append(new_order)
    order_counter += 1
    return {"message": "Order placed", "order": new_order}

# Fetch the complete list of placed orders
@app.get("/orders")
def get_all_orders():
    return {"orders": orders, "total_orders": len(orders)}

# Fetch details of a specific order by ID
@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            return {"order": order}
    return {"error": "Order not found"}

# Update an existing order status to confirmed
@app.patch("/orders/{order_id}/confirm")
def confirm_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            order["status"] = "confirmed"
            return {"message": "Order confirmed", "order": order}
    return {"error": "Order not found"}