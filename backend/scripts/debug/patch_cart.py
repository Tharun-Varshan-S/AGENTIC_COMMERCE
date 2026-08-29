def patch():
    with open("app/services/cart.py", "r") as f:
        content = f.read()

    # Fix 1: _build_cart_response
    old_build = """            prod_resp = ProductResponse(
                id=product.id,
                created_at=product.created_at,
                updated_at=product.updated_at,
                merchant_id=product.merchant_id,
                sku=product.sku,
                name=product.name,
                description=product.description,
                category=product.category,
                brand=product.brand,
                price=product.price,
                cost_price=product.cost_price,
                currency=product.currency,
                is_active=product.is_active,
                metadata_json=product.metadata_json,
                inventory=None
            )"""
            
    new_build = """            # Get the best offer or default
            offer = None
            if hasattr(product, 'offers') and product.offers:
                offer = product.offers[0]
                
            prod_resp = ProductResponse(
                id=product.id,
                created_at=product.created_at,
                updated_at=product.updated_at,
                merchant_id=product.merchant_id,
                sku=product.sku,
                name=product.name,
                description=product.description,
                category=product.category,
                brand=product.brand,
                price=offer.price if offer else 0.0,
                cost_price=None,
                currency="INR",
                is_active=offer.is_active if offer else True,
                metadata_json=product.metadata_json,
                inventory=None
            )"""
            
    content = content.replace(old_build, new_build)
    
    # Fix 2: add_item_to_cart
    old_add_item_check = """        product = self.core_repo.get_product(product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail="Product is unavailable")"""
            
    new_add_item_check = """        product = self.core_repo.get_product(product_id)
        if not product:
            raise HTTPException(status_code=400, detail="Product is unavailable")
            
        offer = None
        if hasattr(product, 'offers') and product.offers:
            active_offers = [o for o in product.offers if o.is_active]
            if active_offers:
                offer = active_offers[0]
                
        if not offer:
            raise HTTPException(status_code=400, detail="Product is unavailable")"""
            
    content = content.replace(old_add_item_check, new_add_item_check)
    
    # Fix 3: add_item_to_cart adding with price
    old_add_item = """        if item:
            self.repo.update_item_quantity(item, current_quantity + quantity)
        else:
            self.repo.add_item(cart_id, product_id, quantity, product.price)"""
            
    new_add_item = """        if item:
            self.repo.update_item_quantity(item, current_quantity + quantity)
        else:
            self.repo.add_item(cart_id, product_id, quantity, offer.price)"""
            
    content = content.replace(old_add_item, new_add_item)

    with open("app/services/cart.py", "w") as f:
        f.write(content)

patch()
