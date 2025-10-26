#!/bin/bash

###############################################################################
# Modula Builder Deployment Script - Modula Side (PHP/Sngine)
# Deploy builder integration to Modula platform
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - UPDATE THESE
MODULA_PATH="/var/www/modula"
WEB_USER="www-data"
DB_HOST="localhost"
DB_NAME="modula_db"
DB_USER="modula_user"

echo -e "${GREEN}Starting Modula Builder Integration Deployment...${NC}"

# Step 1: Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if [ ! -d "$MODULA_PATH" ]; then
    echo -e "${RED}Error: Modula directory not found: $MODULA_PATH${NC}"
    exit 1
fi

if ! command -v php &> /dev/null; then
    echo -e "${RED}Error: PHP not found${NC}"
    exit 1
fi

if ! command -v mysql &> /dev/null; then
    echo -e "${RED}Error: MySQL not found${NC}"
    exit 1
fi

if ! command -v composer &> /dev/null; then
    echo -e "${RED}Error: Composer not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"

# Step 2: Backup database
echo -e "${YELLOW}Backing up database...${NC}"
read -p "Enter MySQL root password: " -s DB_ROOT_PASSWORD
echo ""

BACKUP_FILE="modula_backup_$(date +%Y%m%d_%H%M%S).sql"
mysqldump -h "$DB_HOST" -u root -p"$DB_ROOT_PASSWORD" "$DB_NAME" > "/tmp/$BACKUP_FILE"
echo -e "${GREEN}✓ Backup created: /tmp/$BACKUP_FILE${NC}"

# Step 3: Install PHP dependencies
echo -e "${YELLOW}Installing PHP dependencies...${NC}"
cd "$MODULA_PATH"

if [ ! -f "composer.json" ]; then
    echo "Creating composer.json..."
    cat > composer.json <<EOF
{
    "require": {
        "firebase/php-jwt": "^6.0"
    }
}
EOF
else
    echo "Adding firebase/php-jwt to existing composer.json..."
    composer require firebase/php-jwt
fi

composer install
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 4: Copy integration files
echo -e "${YELLOW}Copying integration files...${NC}"

# Create integration directory
mkdir -p "$MODULA_PATH/includes/builder"

# Copy ModulaBuilderClient.php
if [ -f "ModulaBuilderClient.php" ]; then
    cp ModulaBuilderClient.php "$MODULA_PATH/includes/builder/"
    echo -e "${GREEN}✓ Copied ModulaBuilderClient.php${NC}"
else
    echo -e "${RED}✗ ModulaBuilderClient.php not found${NC}"
    exit 1
fi

# Copy example usage (optional)
if [ -f "example_usage.php" ]; then
    cp example_usage.php "$MODULA_PATH/includes/builder/examples.php"
    echo -e "${GREEN}✓ Copied example_usage.php${NC}"
fi

# Step 5: Apply database schema
echo -e "${YELLOW}Applying database schema...${NC}"

if [ -f "../builder/modula_database_schema.sql" ]; then
    mysql -h "$DB_HOST" -u root -p"$DB_ROOT_PASSWORD" "$DB_NAME" < ../builder/modula_database_schema.sql
    echo -e "${GREEN}✓ Database schema applied${NC}"
else
    echo -e "${RED}✗ Schema file not found${NC}"
    exit 1
fi

# Verify tables were created
TABLE_COUNT=$(mysql -h "$DB_HOST" -u root -p"$DB_ROOT_PASSWORD" "$DB_NAME" -N -e "
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = '$DB_NAME'
    AND table_name LIKE 'modula_builder_%'
")

if [ "$TABLE_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✓ Database tables created ($TABLE_COUNT tables)${NC}"
else
    echo -e "${RED}✗ Expected 4+ tables, found $TABLE_COUNT${NC}"
fi

# Step 6: Configure Modula
echo -e "${YELLOW}Configuring Modula...${NC}"

read -p "Enter Builder URL [https://builder.modula.digital]: " BUILDER_URL
BUILDER_URL=${BUILDER_URL:-https://builder.modula.digital}

read -p "Enter JWT Secret (must match Builder config): " JWT_SECRET
if [ -z "$JWT_SECRET" ]; then
    echo -e "${RED}Error: JWT Secret is required${NC}"
    exit 1
fi

read -p "Enter JWT Algorithm [HS256]: " JWT_ALGORITHM
JWT_ALGORITHM=${JWT_ALGORITHM:-HS256}

# Add configuration to config.php
CONFIG_FILE="$MODULA_PATH/includes/config.php"

if [ -f "$CONFIG_FILE" ]; then
    # Backup config
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

    # Add builder configuration
    cat >> "$CONFIG_FILE" <<EOF

// ============================================================================
// Modula Builder Configuration
// ============================================================================
define('BUILDER_URL', '$BUILDER_URL');
define('BUILDER_API_URL', '${BUILDER_URL}/api/method/builder.modula_api');
define('BUILDER_JWT_SECRET', '$JWT_SECRET');
define('BUILDER_JWT_ALGORITHM', '$JWT_ALGORITHM');
define('BUILDER_CALLBACK_URL', 'https://modula.digital/api/builder/callback.php');

EOF

    echo -e "${GREEN}✓ Configuration added to config.php${NC}"
else
    echo -e "${RED}✗ Config file not found: $CONFIG_FILE${NC}"
    echo "Please manually add configuration"
fi

# Step 7: Create directories
echo -e "${YELLOW}Creating artifact directories...${NC}"

mkdir -p "$MODULA_PATH/content/snippets"
mkdir -p "$MODULA_PATH/content/themes/default/templates/blocks"

chown -R $WEB_USER:$WEB_USER "$MODULA_PATH/content/snippets"
chown -R $WEB_USER:$WEB_USER "$MODULA_PATH/content/themes/default/templates/blocks"

chmod -R 755 "$MODULA_PATH/content/snippets"
chmod -R 755 "$MODULA_PATH/content/themes/default/templates/blocks"

echo -e "${GREEN}✓ Directories created${NC}"

# Step 8: Create API endpoint for callback
echo -e "${YELLOW}Creating API endpoint...${NC}"

mkdir -p "$MODULA_PATH/api/builder"

cat > "$MODULA_PATH/api/builder/callback.php" <<'EOF'
<?php
/**
 * Modula Builder - Publish Callback Endpoint
 * Receives publish notifications from builder.modula.digital
 */

// Bootstrap Sngine
require_once __DIR__ . '/../../includes/config.php';

// Include builder client
require_once __DIR__ . '/../../includes/builder/ModulaBuilderClient.php';

// Initialize builder client
$builder = new ModulaBuilderClient([
    'builder_url' => BUILDER_URL,
    'jwt_secret' => BUILDER_JWT_SECRET,
    'jwt_algorithm' => BUILDER_JWT_ALGORITHM,
    'db' => $db
]);

// Get POST data
$data = json_decode(file_get_contents('php://input'), true);

// Handle callback
$response = $builder->handlePublishCallback($data);

// Send response
header('Content-Type: application/json');
echo json_encode($response);
EOF

chmod 644 "$MODULA_PATH/api/builder/callback.php"
chown $WEB_USER:$WEB_USER "$MODULA_PATH/api/builder/callback.php"

echo -e "${GREEN}✓ API endpoint created${NC}"

# Step 9: Create helper functions
echo -e "${YELLOW}Creating helper functions...${NC}"

cat > "$MODULA_PATH/includes/builder_functions.php" <<'EOF'
<?php
/**
 * Modula Builder Helper Functions
 * Convenience functions for common builder operations
 */

require_once __DIR__ . '/builder/ModulaBuilderClient.php';

/**
 * Get builder client instance
 */
function get_builder_client() {
    global $db;
    static $builder = null;

    if ($builder === null) {
        $builder = new ModulaBuilderClient([
            'builder_url' => BUILDER_URL,
            'jwt_secret' => BUILDER_JWT_SECRET,
            'jwt_algorithm' => BUILDER_JWT_ALGORITHM,
            'db' => $db
        ]);
    }

    return $builder;
}

/**
 * Open builder for editing
 */
function open_builder_session($user_id, $project_id, $type = 'component') {
    $builder = get_builder_client();
    return $builder->createSession($user_id, $project_id, $type);
}

/**
 * Render artifact HTML
 */
function render_builder_artifact($project_id) {
    $builder = get_builder_client();
    return $builder->renderArtifact($project_id);
}

/**
 * Get artifact data
 */
function get_builder_artifact($project_id) {
    $builder = get_builder_client();
    return $builder->getArtifactByProject($project_id);
}

/**
 * Get Smarty template path
 */
function get_builder_template($project_id) {
    $builder = get_builder_client();
    return $builder->getSmartyTemplatePath($project_id);
}
EOF

chmod 644 "$MODULA_PATH/includes/builder_functions.php"
chown $WEB_USER:$WEB_USER "$MODULA_PATH/includes/builder_functions.php"

echo -e "${GREEN}✓ Helper functions created${NC}"

# Step 10: Register Smarty functions
echo -e "${YELLOW}Setting up Smarty integration...${NC}"

cat > "$MODULA_PATH/includes/builder_smarty.php" <<'EOF'
<?php
/**
 * Smarty Functions for Builder Integration
 * Include this file after Smarty initialization
 */

require_once __DIR__ . '/builder_functions.php';

/**
 * {builder_render project="profile_tab_123"}
 */
$smarty->registerPlugin('function', 'builder_render', function($params, $smarty) {
    $project_id = $params['project'] ?? '';
    if ($project_id) {
        return render_builder_artifact($project_id);
    }
    return '';
});

/**
 * {builder_edit_url project="profile_tab_123" type="profile_tab"}
 */
$smarty->registerPlugin('function', 'builder_edit_url', function($params, $smarty) {
    global $user;

    $project_id = $params['project'] ?? '';
    $type = $params['type'] ?? 'component';

    if ($project_id && $user) {
        return open_builder_session($user->user_id, $project_id, $type);
    }

    return '#';
});

/**
 * {builder_exists project="profile_tab_123"}
 */
$smarty->registerPlugin('function', 'builder_exists', function($params, $smarty) {
    $project_id = $params['project'] ?? '';
    return get_builder_artifact($project_id) ? '1' : '0';
});
EOF

chmod 644 "$MODULA_PATH/includes/builder_smarty.php"
chown $WEB_USER:$WEB_USER "$MODULA_PATH/includes/builder_smarty.php"

echo -e "${GREEN}✓ Smarty functions created${NC}"

# Step 11: Set permissions
echo -e "${YELLOW}Setting permissions...${NC}"

chown -R $WEB_USER:$WEB_USER "$MODULA_PATH/includes/builder"
chmod -R 644 "$MODULA_PATH/includes/builder"/*.php
find "$MODULA_PATH/includes/builder" -type d -exec chmod 755 {} \;

echo -e "${GREEN}✓ Permissions set${NC}"

# Step 12: Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"

TEST_RESULT=$(mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_ROOT_PASSWORD" "$DB_NAME" -N -e "
    SELECT COUNT(*) FROM modula_builder_artifacts
" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo "$TEST_RESULT"
fi

# Step 13: Clear cache (if applicable)
echo -e "${YELLOW}Clearing cache...${NC}"

if [ -d "$MODULA_PATH/cache" ]; then
    rm -rf "$MODULA_PATH/cache"/*
    echo -e "${GREEN}✓ Cache cleared${NC}"
fi

# Step 14: Display summary
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Modula Builder Integration Deployed! ${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo "Builder URL: $BUILDER_URL"
echo "Callback URL: https://modula.digital/api/builder/callback.php"
echo "JWT Algorithm: $JWT_ALGORITHM"
echo ""
echo -e "${YELLOW}Files Created:${NC}"
echo "  • $MODULA_PATH/includes/builder/ModulaBuilderClient.php"
echo "  • $MODULA_PATH/includes/builder_functions.php"
echo "  • $MODULA_PATH/includes/builder_smarty.php"
echo "  • $MODULA_PATH/api/builder/callback.php"
echo ""
echo -e "${YELLOW}Directories Created:${NC}"
echo "  • $MODULA_PATH/content/snippets/"
echo "  • $MODULA_PATH/content/themes/default/templates/blocks/"
echo ""
echo -e "${YELLOW}Database Tables:${NC}"
echo "  • modula_builder_artifacts"
echo "  • modula_builder_versions"
echo "  • modula_builder_deployments"
echo "  • modula_builder_sessions"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Add to your main init file:"
echo "   require_once __DIR__ . '/includes/builder_functions.php';"
echo ""
echo "2. After Smarty initialization, add:"
echo "   require_once __DIR__ . '/includes/builder_smarty.php';"
echo ""
echo "3. Test by creating a session:"
echo "   \$url = open_builder_session(\$user->user_id, 'test_project', 'widget');"
echo "   redirect(\$url);"
echo ""
echo "4. Configure Builder side (run deploy_builder.sh on builder server)"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "  See README.md and example_usage.php for integration examples"
echo ""

echo -e "${GREEN}Deployment completed successfully!${NC}"
