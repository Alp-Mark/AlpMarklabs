#!/bin/bash
# Wipe One8 data and reseed with realistic patterns on Railway production

echo "🚀 Deploying realistic data seeding script to Railway..."

# Commit the script
git add scripts/seed_one8_realistic.py
git commit -m "feat: realistic One8 data seeding with seasonality and saturation"

# Push to trigger deploy
git push origin main

echo ""
echo "✅ Pushed to Railway. Deployment starting..."
echo ""
echo "To run the seeding script on Railway:"
echo "1. Wait for deployment to complete (2-3 minutes)"
echo "2. Run: railway run --service AlpMarklabs bash -c 'cd /app && python3 scripts/seed_one8_realistic.py'"
echo ""
echo "OR use Railway dashboard:"
echo "1. Go to Railway dashboard"
echo "2. Open AlpMarklabs service"  
echo "3. Click 'Terminal' or 'Shell'"
echo "4. Run: python3 scripts/seed_one8_realistic.py"
