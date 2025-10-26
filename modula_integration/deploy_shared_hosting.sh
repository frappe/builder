#!/bin/bash

###############################################################################
# Modula Builder Deployment Script - SHARED HOSTING Edition
# Deploy builder integration to shared hosting environment (cPanel, Plesk, etc.)
###############################################################################

# NO root/sudo required - works with standard shared hosting

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Modula Builder - Shared Hosting Deployment ${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Get configuration
echo -e "${BLUE}Step 1: Configuration${NC}"
echo "Please provide the following information:"
echo ""

read -p "Enter your public_html path [~/public_html]: " PUBLIC_HTML
PUBLIC_HTML=${PUBLIC_HTML:-~/public_html}

# Expand ~ to actual home directory
PUBLIC_HTML="${PUBLIC_HTML/#\~/$HOME}"

if [ ! -d "$PUBLIC_HTML" ]; then
    echo -e "${RED}Error: Directory not found: $PUBLIC_HTML${NC}"
    echo "Common paths: ~/public_html, ~/www, ~/htdocs"
    exit 1
fi

echo -e "${GREEN}✓ Found public_html: $PUBLIC_HTML${NC}"

read -p "Enter Builder URL [https://builder.modula.digital]: " BUILDER_URL
BUILDER_URL=${BUILDER_URL:-https://builder.modula.digital}

read -p "Enter JWT Secret (same as Builder config): " JWT_SECRET
if [ -z "$JWT_SECRET" ]; then
    echo -e "${RED}Error: JWT Secret is required${NC}"
    exit 1
fi

read -p "Enter JWT Algorithm [HS256]: " JWT_ALGORITHM
JWT_ALGORITHM=${JWT_ALGORITHM:-HS256}

echo ""
echo -e "${YELLOW}Database Configuration${NC}"
echo "You'll need to create database tables manually via phpMyAdmin"
read -p "Press Enter to continue..."

# Step 2: Create directory structure
echo ""
echo -e "${BLUE}Step 2: Creating directory structure${NC}"

mkdir -p "$PUBLIC_HTML/includes/builder"
mkdir -p "$PUBLIC_HTML/api/builder"
mkdir -p "$PUBLIC_HTML/content/snippets"
mkdir -p "$PUBLIC_HTML/content/themes/default/templates/blocks"

echo -e "${GREEN}✓ Directories created${NC}"

# Step 3: Copy integration files
echo ""
echo -e "${BLUE}Step 3: Installing integration files${NC}"

# Copy shared hosting version of ModulaBuilderClient
if [ -f "ModulaBuilderClient_SharedHosting.php" ]; then
    cp ModulaBuilderClient_SharedHosting.php "$PUBLIC_HTML/includes/builder/ModulaBuilderClient.php"
    echo -e "${GREEN}✓ Copied ModulaBuilderClient.php${NC}"
else
    echo -e "${RED}✗ ModulaBuilderClient_SharedHosting.php not found${NC}"
    exit 1
fi

# Copy JWT fallback
if [ -f "jwt_fallback.php" ]; then
    cp jwt_fallback.php "$PUBLIC_HTML/includes/builder/"
    echo -e "${GREEN}✓ Copied jwt_fallback.php${NC}"
fi

# Copy example usage
if [ -f "example_usage.php" ]; then
    cp example_usage.php "$PUBLIC_HTML/includes/builder/examples.php"
    echo -e "${GREEN}✓ Copied examples.php${NC}"
fi

# Step 4: Create helper functions
echo ""
echo -e "${BLUE}Step 4: Creating helper functions${NC}"

cat > "$PUBLIC_HTML/includes/builder_functions.php" <<'EOF'
<?php
/**
 * Modula Builder Helper Functions - Shared Hosting Edition
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
            'jwt_algorithm' => BUILDER_JWT_ALGORITHM ?? 'HS256',
            'db' => $db,
            'base_path' => dirname(__DIR__)  // Relative to includes/
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
    $fullPath = $builder->getSmartyTemplatePath($project_id);

    if ($fullPath) {
        // Return relative path for Smarty
        return basename($fullPath);
    }

    return null;
}
EOF

echo -e "${GREEN}✓ Created builder_functions.php${NC}"

# Step 5: Create Smarty integration
cat > "$PUBLIC_HTML/includes/builder_smarty.php" <<'EOF'
<?php
/**
 * Smarty Functions for Builder - Shared Hosting Edition
 */

require_once __DIR__ . '/builder_functions.php';

// {builder_render project="profile_tab_123"}
$smarty->registerPlugin('function', 'builder_render', function($params, $smarty) {
    $project_id = $params['project'] ?? '';
    if ($project_id) {
        return render_builder_artifact($project_id);
    }
    return '';
});

// {builder_edit_url project="profile_tab_123" type="profile_tab"}
$smarty->registerPlugin('function', 'builder_edit_url', function($params, $smarty) {
    global $user;

    $project_id = $params['project'] ?? '';
    $type = $params['type'] ?? 'component';

    if ($project_id && $user) {
        return open_builder_session($user->user_id, $project_id, $type);
    }

    return '#';
});

// {builder_exists project="profile_tab_123"}
$smarty->registerPlugin('function', 'builder_exists', function($params, $smarty) {
    $project_id = $params['project'] ?? '';
    return get_builder_artifact($project_id) ? '1' : '0';
});
EOF

echo -e "${GREEN}✓ Created builder_smarty.php${NC}"

# Step 6: Create API callback endpoint
echo ""
echo -e "${BLUE}Step 5: Creating API endpoint${NC}"

cat > "$PUBLIC_HTML/api/builder/callback.php" <<'EOF'
<?php
/**
 * Modula Builder - Publish Callback Endpoint
 * Receives notifications from builder.modula.digital
 */

// Bootstrap your application
// Adjust this path to match your setup
$bootstrap_path = dirname(dirname(__DIR__)) . '/includes/config.php';

if (file_exists($bootstrap_path)) {
    require_once $bootstrap_path;
} else {
    // Fallback - adjust as needed
    require_once '../../includes/config.php';
}

// Include builder client
require_once dirname(dirname(__DIR__)) . '/includes/builder/ModulaBuilderClient.php';

// Initialize builder client
$builder = new ModulaBuilderClient([
    'builder_url' => BUILDER_URL,
    'jwt_secret' => BUILDER_JWT_SECRET,
    'jwt_algorithm' => BUILDER_JWT_ALGORITHM ?? 'HS256',
    'db' => $db,
    'base_path' => dirname(dirname(__DIR__))
]);

// Get POST data
$data = json_decode(file_get_contents('php://input'), true);

// Handle callback
$response = $builder->handlePublishCallback($data);

// Send response
header('Content-Type: application/json');
echo json_encode($response);
EOF

echo -e "${GREEN}✓ Created callback.php${NC}"

# Step 7: Copy .htaccess
if [ -f ".htaccess_api" ]; then
    cp .htaccess_api "$PUBLIC_HTML/api/builder/.htaccess"
    echo -e "${GREEN}✓ Copied .htaccess for API${NC}"
fi

# Step 8: Create config snippet
echo ""
echo -e "${BLUE}Step 6: Creating configuration snippet${NC}"

cat > "$PUBLIC_HTML/includes/builder_config.php" <<EOF
<?php
/**
 * Modula Builder Configuration
 * Include this in your main config file
 */

// Builder Settings
define('BUILDER_URL', '$BUILDER_URL');
define('BUILDER_API_URL', '${BUILDER_URL}/api/method/builder.modula_api');
define('BUILDER_JWT_SECRET', '$JWT_SECRET');
define('BUILDER_JWT_ALGORITHM', '$JWT_ALGORITHM');
define('BUILDER_CALLBACK_URL', 'https://' . \$_SERVER['HTTP_HOST'] . '/api/builder/callback.php');
EOF

echo -e "${GREEN}✓ Created builder_config.php${NC}"

# Step 9: Create database setup file
echo ""
echo -e "${BLUE}Step 7: Creating database setup file${NC}"

if [ -f "../builder/modula_database_schema.sql" ]; then
    cp ../builder/modula_database_schema.sql "$PUBLIC_HTML/setup_database.sql"
    echo -e "${GREEN}✓ Copied database schema${NC}"
    echo -e "${YELLOW}  → Import this file via phpMyAdmin: $PUBLIC_HTML/setup_database.sql${NC}"
fi

# Step 10: Set permissions (what we can set without sudo)
echo ""
echo -e "${BLUE}Step 8: Setting permissions${NC}"

chmod 644 "$PUBLIC_HTML/includes/builder"/*.php 2>/dev/null || true
chmod 644 "$PUBLIC_HTML/includes/builder_functions.php" 2>/dev/null || true
chmod 644 "$PUBLIC_HTML/includes/builder_smarty.php" 2>/dev/null || true
chmod 644 "$PUBLIC_HTML/includes/builder_config.php" 2>/dev/null || true
chmod 644 "$PUBLIC_HTML/api/builder/callback.php" 2>/dev/null || true
chmod 755 "$PUBLIC_HTML/content/snippets" 2>/dev/null || true
chmod 755 "$PUBLIC_HTML/content/themes/default/templates/blocks" 2>/dev/null || true

echo -e "${GREEN}✓ Permissions set${NC}"

# Step 11: Try Composer (optional)
echo ""
echo -e "${BLUE}Step 9: PHP Dependencies (optional)${NC}"
echo "Trying to install firebase/php-jwt via Composer..."

cd "$PUBLIC_HTML"

if command -v composer &> /dev/null; then
    if [ ! -f "composer.json" ]; then
        echo '{"require": {"firebase/php-jwt": "^6.0"}}' > composer.json
    fi

    composer install --no-dev 2>/dev/null && echo -e "${GREEN}✓ Composer packages installed${NC}" || echo -e "${YELLOW}⚠ Composer install failed - using JWT fallback${NC}"
else
    echo -e "${YELLOW}⚠ Composer not found - using JWT fallback implementation${NC}"
    echo "  This is fine for shared hosting. The fallback JWT library will be used."
fi

# Step 12: Create test file
echo ""
echo -e "${BLUE}Step 10: Creating test file${NC}"

cat > "$PUBLIC_HTML/test_builder.php" <<'EOF'
<?php
/**
 * Test Builder Integration
 * Visit: https://yourdomain.com/test_builder.php
 */

require_once 'includes/config.php';
require_once 'includes/builder_config.php';
require_once 'includes/builder_functions.php';

header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html>
<head>
    <title>Builder Integration Test</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .success { color: green; }
        .error { color: red; }
        .info { background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0; }
        code { background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🔧 Builder Integration Test</h1>

    <?php
    // Test 1: Check constants
    echo "<h2>1. Configuration Check</h2>";
    if (defined('BUILDER_URL')) {
        echo "<p class='success'>✓ BUILDER_URL: " . BUILDER_URL . "</p>";
    } else {
        echo "<p class='error'>✗ BUILDER_URL not defined</p>";
    }

    if (defined('BUILDER_JWT_SECRET')) {
        echo "<p class='success'>✓ JWT Secret configured</p>";
    } else {
        echo "<p class='error'>✗ JWT Secret not configured</p>";
    }

    // Test 2: Check files
    echo "<h2>2. File Check</h2>";
    $files = [
        'includes/builder/ModulaBuilderClient.php',
        'includes/builder_functions.php',
        'includes/builder_smarty.php',
        'api/builder/callback.php'
    ];

    foreach ($files as $file) {
        if (file_exists($file)) {
            echo "<p class='success'>✓ {$file}</p>";
        } else {
            echo "<p class='error'>✗ {$file} not found</p>";
        }
    }

    // Test 3: Check database
    echo "<h2>3. Database Check</h2>";
    if (isset($db)) {
        $tables = [
            'modula_builder_artifacts',
            'modula_builder_versions',
            'modula_builder_deployments',
            'modula_builder_sessions'
        ];

        foreach ($tables as $table) {
            $result = $db->query("SHOW TABLES LIKE '{$table}'");
            if ($result && $result->num_rows > 0) {
                echo "<p class='success'>✓ Table exists: {$table}</p>";
            } else {
                echo "<p class='error'>✗ Table missing: {$table} - Import setup_database.sql via phpMyAdmin</p>";
            }
        }
    } else {
        echo "<p class='error'>✗ Database connection not available</p>";
    }

    // Test 4: Create test session (if user logged in)
    echo "<h2>4. Session Test</h2>";
    if (isset($user) && $user->user_id) {
        try {
            $url = open_builder_session($user->user_id, 'test_project_001', 'widget');
            echo "<p class='success'>✓ Session created successfully!</p>";
            echo "<div class='info'>";
            echo "<strong>Builder URL:</strong><br>";
            echo "<code>" . htmlspecialchars($url) . "</code><br><br>";
            echo "<a href='{$url}' target='_blank' style='background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;'>Open Builder →</a>";
            echo "</div>";
        } catch (Exception $e) {
            echo "<p class='error'>✗ Error: " . $e->getMessage() . "</p>";
        }
    } else {
        echo "<p>⚠ Please log in to test session creation</p>";
    }

    // Test 5: Next steps
    echo "<h2>5. Next Steps</h2>";
    echo "<ol>";
    echo "<li>If database tables are missing, import <code>setup_database.sql</code> via phpMyAdmin</li>";
    echo "<li>Add to your config file: <code>require_once 'includes/builder_config.php';</code></li>";
    echo "<li>Add to your init file: <code>require_once 'includes/builder_functions.php';</code></li>";
    echo "<li>After Smarty init: <code>require_once 'includes/builder_smarty.php';</code></li>";
    echo "<li>Delete this test file for security: <code>test_builder.php</code></li>";
    echo "</ol>";
    ?>

    <hr>
    <p><small>Modula Builder Integration - Shared Hosting Edition</small></p>
</body>
</html>
EOF

echo -e "${GREEN}✓ Created test_builder.php${NC}"

# Final summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Deployment Complete! ${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📁 Files Created:${NC}"
echo "  • $PUBLIC_HTML/includes/builder/ModulaBuilderClient.php"
echo "  • $PUBLIC_HTML/includes/builder/jwt_fallback.php"
echo "  • $PUBLIC_HTML/includes/builder_functions.php"
echo "  • $PUBLIC_HTML/includes/builder_smarty.php"
echo "  • $PUBLIC_HTML/includes/builder_config.php"
echo "  • $PUBLIC_HTML/api/builder/callback.php"
echo "  • $PUBLIC_HTML/api/builder/.htaccess"
echo "  • $PUBLIC_HTML/test_builder.php"
echo "  • $PUBLIC_HTML/setup_database.sql"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo ""
echo "1. ${BLUE}Setup Database:${NC}"
echo "   - Log into phpMyAdmin"
echo "   - Select your database"
echo "   - Import: $PUBLIC_HTML/setup_database.sql"
echo ""
echo "2. ${BLUE}Update Your Config:${NC}"
echo "   Add to your includes/config.php:"
echo "   ${GREEN}require_once __DIR__ . '/builder_config.php';${NC}"
echo ""
echo "3. ${BLUE}Update Your Init File:${NC}"
echo "   Add to your init file:"
echo "   ${GREEN}require_once __DIR__ . '/builder_functions.php';${NC}"
echo ""
echo "4. ${BLUE}Update Smarty Init:${NC}"
echo "   After Smarty initialization:"
echo "   ${GREEN}require_once __DIR__ . '/builder_smarty.php';${NC}"
echo ""
echo "5. ${BLUE}Test Integration:${NC}"
echo "   Visit: ${GREEN}https://yourdomain.com/test_builder.php${NC}"
echo ""
echo "6. ${BLUE}Configure Builder Server:${NC}"
echo "   Run on builder.modula.digital server:"
echo "   ${GREEN}./deploy_builder.sh${NC}"
echo ""
echo -e "${YELLOW}🔐 Security:${NC}"
echo "  • Delete test_builder.php after testing"
echo "  • Delete setup_database.sql after importing"
echo "  • Keep JWT secret secure (never commit to git)"
echo ""
echo -e "${YELLOW}📚 Documentation:${NC}"
echo "  • See: modula_integration/README.md"
echo "  • Examples: includes/builder/examples.php"
echo "  • Quick start: QUICKSTART.md"
echo ""
echo -e "${GREEN}✨ Integration ready for shared hosting!${NC}"
