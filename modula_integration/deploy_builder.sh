#!/bin/bash

###############################################################################
# Modula Builder Deployment Script - Builder Side (Frappe)
# Deploy builder.modula.digital with Modula integration
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SITE_NAME="builder.modula.digital"
BENCH_PATH="/home/frappe/frappe-bench"
APP_NAME="builder"

echo -e "${GREEN}Starting Modula Builder deployment...${NC}"

# Step 1: Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v bench &> /dev/null; then
    echo -e "${RED}Error: Frappe Bench not found${NC}"
    exit 1
fi

if [ ! -d "$BENCH_PATH" ]; then
    echo -e "${RED}Error: Bench directory not found: $BENCH_PATH${NC}"
    exit 1
fi

cd "$BENCH_PATH"

# Step 2: Backup existing site (if exists)
if bench --site "$SITE_NAME" list-apps &> /dev/null; then
    echo -e "${YELLOW}Backing up existing site...${NC}"
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    bench --site "$SITE_NAME" backup --backup-path-db "/tmp/$BACKUP_FILE"
    echo -e "${GREEN}Backup created: /tmp/$BACKUP_FILE${NC}"
fi

# Step 3: Pull latest code
echo -e "${YELLOW}Pulling latest code...${NC}"
cd "apps/$APP_NAME"
git fetch origin
git checkout claude/create-modula-builder-011CUUj7xJRRSdAdrAa9L4zr
git pull origin claude/create-modula-builder-011CUUj7xJRRSdAdrAa9L4zr
cd ../..

# Step 4: Install/update app
echo -e "${YELLOW}Installing/updating app...${NC}"
if bench --site "$SITE_NAME" list-apps | grep -q "$APP_NAME"; then
    echo "App already installed, migrating..."
    bench --site "$SITE_NAME" migrate
else
    echo "Installing app..."
    bench --site "$SITE_NAME" install-app "$APP_NAME"
fi

# Step 5: Install custom fields
echo -e "${YELLOW}Installing custom fields...${NC}"
bench --site "$SITE_NAME" execute "
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import json

with open('apps/builder/builder/fixtures/custom_fields.json', 'r') as f:
    custom_fields = json.load(f)

for field in custom_fields:
    if not frappe.db.exists('Custom Field', field.get('fieldname')):
        doc = frappe.get_doc(field)
        doc.insert(ignore_permissions=True)

frappe.db.commit()
"

# Step 6: Configure site
echo -e "${YELLOW}Configuring site...${NC}"

# Prompt for configuration values
read -p "Enter Modula API URL [https://modula.digital]: " MODULA_API_URL
MODULA_API_URL=${MODULA_API_URL:-https://modula.digital}

read -p "Enter JWT Secret (same as in Modula config): " JWT_SECRET
if [ -z "$JWT_SECRET" ]; then
    echo -e "${RED}Error: JWT Secret is required${NC}"
    exit 1
fi

read -p "Enter JWT Algorithm [HS256]: " JWT_ALGORITHM
JWT_ALGORITHM=${JWT_ALGORITHM:-HS256}

read -p "Enter snippets path [/var/www/modula/content/snippets]: " SNIPPETS_PATH
SNIPPETS_PATH=${SNIPPETS_PATH:-/var/www/modula/content/snippets}

read -p "Enter templates path [/var/www/modula/content/themes/default/templates/blocks]: " TEMPLATES_PATH
TEMPLATES_PATH=${TEMPLATES_PATH:-/var/www/modula/content/themes/default/templates/blocks}

# Set configuration
bench --site "$SITE_NAME" set-config modula_api_url "$MODULA_API_URL"
bench --site "$SITE_NAME" set-config modula_jwt_secret "$JWT_SECRET"
bench --site "$SITE_NAME" set-config modula_jwt_algorithm "$JWT_ALGORITHM"
bench --site "$SITE_NAME" set-config modula_snippets_path "$SNIPPETS_PATH"
bench --site "$SITE_NAME" set-config modula_templates_path "$TEMPLATES_PATH"

echo -e "${GREEN}Configuration updated${NC}"

# Step 7: Create directories with proper permissions
echo -e "${YELLOW}Creating artifact directories...${NC}"
sudo mkdir -p "$SNIPPETS_PATH"
sudo mkdir -p "$TEMPLATES_PATH"
sudo chown -R frappe:frappe "$SNIPPETS_PATH"
sudo chown -R frappe:frappe "$TEMPLATES_PATH"
sudo chmod -R 755 "$SNIPPETS_PATH"
sudo chmod -R 755 "$TEMPLATES_PATH"

# Step 8: Build assets
echo -e "${YELLOW}Building frontend assets...${NC}"
bench build --app builder

# Step 9: Clear cache
echo -e "${YELLOW}Clearing cache...${NC}"
bench --site "$SITE_NAME" clear-cache
bench --site "$SITE_NAME" clear-website-cache

# Step 10: Restart services
echo -e "${YELLOW}Restarting services...${NC}"
bench restart

# Step 11: Setup SSL (optional)
read -p "Setup SSL certificate with Let's Encrypt? (y/n): " SETUP_SSL
if [ "$SETUP_SSL" = "y" ] || [ "$SETUP_SSL" = "Y" ]; then
    echo -e "${YELLOW}Setting up SSL...${NC}"
    sudo bench setup lets-encrypt "$SITE_NAME"
fi

# Step 12: Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"

# Check if site is accessible
if bench --site "$SITE_NAME" console <<< "print('OK')" | grep -q "OK"; then
    echo -e "${GREEN}✓ Site is accessible${NC}"
else
    echo -e "${RED}✗ Site verification failed${NC}"
    exit 1
fi

# Check if custom fields exist
FIELDS_COUNT=$(bench --site "$SITE_NAME" execute "
import frappe
count = frappe.db.count('Custom Field', {'dt': 'Builder Page', 'fieldname': ['like', 'modula_%']})
print(count)
" | tail -n 1)

if [ "$FIELDS_COUNT" -ge 6 ]; then
    echo -e "${GREEN}✓ Custom fields installed ($FIELDS_COUNT fields)${NC}"
else
    echo -e "${RED}✗ Custom fields incomplete (found $FIELDS_COUNT, expected 6+)${NC}"
fi

# Check API endpoints
API_CHECK=$(bench --site "$SITE_NAME" execute "
import frappe
from builder import modula_api
print('OK' if hasattr(modula_api, 'validate_token') else 'FAIL')
" | tail -n 1)

if [ "$API_CHECK" = "OK" ]; then
    echo -e "${GREEN}✓ Modula API endpoints available${NC}"
else
    echo -e "${RED}✗ Modula API endpoints not found${NC}"
fi

# Step 13: Display summary
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Modula Builder Deployment Complete! ${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo "Site URL: https://$SITE_NAME"
echo "Modula API: $MODULA_API_URL"
echo "JWT Algorithm: $JWT_ALGORITHM"
echo "Snippets Path: $SNIPPETS_PATH"
echo "Templates Path: $TEMPLATES_PATH"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure Modula side (see deploy_modula.sh)"
echo "2. Test session creation from Modula"
echo "3. Test publish callback"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs: bench --site $SITE_NAME console"
echo "  Restart: bench restart"
echo "  Update: bench --site $SITE_NAME migrate"
echo ""

# Optional: Run tests
read -p "Run integration tests? (y/n): " RUN_TESTS
if [ "$RUN_TESTS" = "y" ] || [ "$RUN_TESTS" = "Y" ]; then
    echo -e "${YELLOW}Running tests...${NC}"
    # Add test commands here
    echo "Tests would run here (not implemented yet)"
fi

echo -e "${GREEN}Deployment script completed successfully!${NC}"
