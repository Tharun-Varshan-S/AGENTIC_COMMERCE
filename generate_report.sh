#!/bin/bash

echo "1. FILE TREE:"
find . -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.next/*' 2>/dev/null || echo "does not exist"
echo ""

echo "2. PACKAGE.JSON:"
if [ -f package.json ]; then cat package.json; else echo "does not exist"; fi
if [ -f frontend/package.json ]; then echo -e "\n--- frontend/package.json ---\n"; cat frontend/package.json; fi
echo ""

echo "3. ENV VARS PRESENT:"
grep -oE '^[A-Z_]+=' .env.local .env.local.example frontend/.env.local frontend/.env.local.example backend/.env backend/.env.example 2>/dev/null || echo "does not exist"
echo ""

echo "4. PRISMA SCHEMA:"
if [ -f prisma/schema.prisma ]; then cat prisma/schema.prisma; elif [ -f backend/prisma/schema.prisma ]; then cat backend/prisma/schema.prisma; else echo "does not exist"; fi
echo ""

echo "5. MIGRATION HISTORY:"
if [ -d prisma/migrations ]; then
    ls -la prisma/migrations/
    for f in prisma/migrations/*.sql; do
        if [ -f "$f" ]; then
            echo "$f"
            head -n 5 "$f"
        fi
    done
elif [ -d backend/prisma/migrations ]; then
    ls -la backend/prisma/migrations/
    for f in backend/prisma/migrations/*.sql; do
        if [ -f "$f" ]; then
            echo "$f"
            head -n 5 "$f"
        fi
    done
else
    echo "does not exist"
fi
echo ""

echo "6. SCHEMA DRIFT CHECK:"
npx -y prisma@latest migrate status || cd backend && npx -y prisma@latest migrate status || echo "does not exist or failed"
echo ""

echo "7. ALL ROUTE HANDLERS:"
found=0
for f in $(find . -path '*/src/app/api/*/route.ts' 2>/dev/null); do
    echo "--- $f ---"
    cat "$f"
    found=1
done
for f in $(find . -path '*/app/api/*/route.ts' 2>/dev/null); do
    echo "--- $f ---"
    cat "$f"
    found=1
done
if [ $found -eq 0 ]; then echo "does not exist"; fi
echo ""

echo "8. ALL LIB FILES:"
found=0
for f in $(find . -path '*/src/lib/*' -type f 2>/dev/null); do
    echo "--- $f ---"
    cat "$f"
    found=1
done
for f in $(find . -path '*/lib/*' -not -path '*/node_modules/*' -type f 2>/dev/null); do
    echo "--- $f ---"
    cat "$f"
    found=1
done
if [ $found -eq 0 ]; then echo "does not exist"; fi
echo ""

echo "9. ALL COMPONENTS:"
found=0
for f in $(find . -path '*/src/components/*' -type f 2>/dev/null); do
    echo "--- $f ---"
    cat "$f"
    found=1
done
for f in $(find . -path '*/components/*' -not -path '*/node_modules/*' -type f 2>/dev/null); do
    echo "--- $f ---"
    cat "$f"
    found=1
done
if [ $found -eq 0 ]; then echo "does not exist"; fi
echo ""

echo "10. TYPESCRIPT HEALTH:"
npx -y typescript@latest tsc --noEmit || (cd frontend && npx -y typescript@latest tsc --noEmit) || echo "failed"
echo ""

echo "11. GIT STATE:"
git status
echo "---"
git log --oneline -20
echo ""

echo "12. RUNTIME ERRORS:"
echo "does not exist"
