from sqlalchemy import select, or_

def fix_merchants():
    content = ""
    with open("app/agent/merchants.py", "r") as f:
        content = f.read()
    
    # We will replace the strict filtering logic
    import re
    # We need to find the `BaseDBMerchant.search_catalog` and rewrite its where clause.
    old_logic = """        if query:
            stmt = stmt.where(Product.name.ilike(f"%{query}%"))
        if category:
            stmt = stmt.where(Product.category.ilike(f"%{category}%"))"""
            
    new_logic = """        from sqlalchemy import or_
        if query and category:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(f"%{query}%"),
                    Product.name.ilike(f"%{category}%"),
                    Product.category.ilike(f"%{query}%"),
                    Product.category.ilike(f"%{category}%")
                )
            )
        elif query:
            stmt = stmt.where(or_(Product.name.ilike(f"%{query}%"), Product.category.ilike(f"%{query}%")))
        elif category:
            stmt = stmt.where(or_(Product.name.ilike(f"%{category}%"), Product.category.ilike(f"%{category}%")))"""
            
    new_content = content.replace(old_logic, new_logic)
    
    with open("app/agent/merchants.py", "w") as f:
        f.write(new_content)

fix_merchants()
