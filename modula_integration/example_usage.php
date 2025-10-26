<?php

/**
 * Modula Builder Integration - Example Usage
 *
 * This file demonstrates how to integrate Modula Builder into your Sngine/Modula application
 */

require_once 'ModulaBuilderClient.php';

// ============================================================================
// Configuration
// ============================================================================

$builderConfig = [
    'builder_url' => 'https://builder.modula.digital',
    'jwt_secret' => 'your-shared-secret-key',  // Must match Frappe Builder config
    'jwt_algorithm' => 'HS256',
    'db' => $db  // Your Sngine database connection
];

$builder = new ModulaBuilderClient($builderConfig);


// ============================================================================
// Example 1: Open Builder for Profile Tab Editing
// ============================================================================

/**
 * User clicks "Edit Profile Tab" in Modula
 */
function open_profile_tab_editor($user, $project_id)
{
    global $builder;

    // Create session and get builder URL
    $builderUrl = $builder->createSession(
        $user->user_id,
        $project_id,
        'profile_tab',
        [
            'permissions' => ['edit', 'publish'],
            'expires_in' => 7200  // 2 hours
        ]
    );

    // Redirect user to builder
    header("Location: {$builderUrl}");
    exit;
}

// Usage in your controller:
// open_profile_tab_editor($user, 'proj_profile_header_123');


// ============================================================================
// Example 2: Handle Publish Callback from Builder
// ============================================================================

/**
 * Builder calls this endpoint after user clicks "Publish"
 * Setup route: POST /api/builder/callback
 */
function handle_builder_callback()
{
    global $builder;

    // Get POST data
    $data = json_decode(file_get_contents('php://input'), true);

    // Handle callback
    $response = $builder->handlePublishCallback($data);

    // Send response
    header('Content-Type: application/json');
    echo json_encode($response);
}

// In your routes/API:
// if ($_SERVER['REQUEST_URI'] === '/api/builder/callback' && $_SERVER['REQUEST_METHOD'] === 'POST') {
//     handle_builder_callback();
// }


// ============================================================================
// Example 3: Render Published Artifact in Profile Page
// ============================================================================

/**
 * Display published build in profile page
 */
function render_profile_tab($project_id)
{
    global $builder;

    // Get HTML fragment
    $html = $builder->renderArtifact($project_id);

    echo $html;
}

// In your profile template (profile.tpl):
// <?php render_profile_tab('proj_profile_header_123'); ?>


// ============================================================================
// Example 4: Include Smarty Template
// ============================================================================

/**
 * Get Smarty template path for inclusion
 */
function get_profile_template($project_id)
{
    global $builder;

    $templatePath = $builder->getSmartyTemplatePath($project_id);

    if ($templatePath) {
        return basename($templatePath);
    }

    return null;
}

// In your Smarty template:
// {$template = get_profile_template('proj_profile_header_123')}
// {if $template}
//   {include file="blocks/{$template}"}
// {/if}


// ============================================================================
// Example 5: Create Widget Builder Session
// ============================================================================

/**
 * Open builder for creating a widget
 */
function create_new_widget($user, $widget_type = 'general')
{
    global $builder;

    // Generate unique project ID
    $project_id = 'widget_' . uniqid();

    // Open builder
    $builderUrl = $builder->createSession(
        $user->user_id,
        $project_id,
        'widget'
    );

    header("Location: {$builderUrl}");
    exit;
}


// ============================================================================
// Example 6: Advanced - Custom Builder Client with Hooks
// ============================================================================

/**
 * Extended builder client with custom publish hooks
 */
class MyModulaBuilderClient extends ModulaBuilderClient
{
    /**
     * Override onPublish to add custom behavior
     */
    protected function onPublish(
        string $projectId,
        string $buildCode,
        string $version,
        int $artifactId
    ): void {
        // Clear profile cache
        $this->clearProfileCache($projectId);

        // Send notification to project owner
        $this->notifyProjectOwner($projectId, $version);

        // Log activity
        $this->logActivity($projectId, "Published version {$version}");

        // Trigger auto-deployment if enabled
        if ($this->isAutoDeployEnabled($projectId)) {
            $this->deployToProduction($artifactId);
        }
    }

    private function clearProfileCache(string $projectId)
    {
        // Clear your cache system
        // cache_delete("profile_{$projectId}");
    }

    private function notifyProjectOwner(string $projectId, string $version)
    {
        // Send notification
        // notify_user($owner_id, "Build published: version {$version}");
    }

    private function logActivity(string $projectId, string $message)
    {
        // Log to activity table
        error_log("[Builder] {$projectId}: {$message}");
    }

    private function isAutoDeployEnabled(string $projectId): bool
    {
        // Check project settings
        return false;
    }

    private function deployToProduction(int $artifactId)
    {
        // Deployment logic
    }
}


// ============================================================================
// Example 7: Profile Page with Builder Integration
// ============================================================================

/**
 * Complete profile page example
 */
class ProfileController
{
    private $builder;
    private $user;

    public function __construct($builder, $user)
    {
        $this->builder = $builder;
        $this->user = $user;
    }

    /**
     * Show profile page
     */
    public function show($profile_user_id)
    {
        // Get profile data
        $profile = $this->getProfileData($profile_user_id);

        // Check if user has custom profile tab
        $project_id = "profile_tab_{$profile_user_id}";
        $customTab = $this->builder->getArtifactByProject($project_id);

        // Render profile
        include 'templates/profile.tpl';
    }

    /**
     * Edit profile tab
     */
    public function editTab()
    {
        // Only owner can edit
        if (!$this->canEdit()) {
            redirect('/error/403');
        }

        // Open builder
        $project_id = "profile_tab_{$this->user->user_id}";

        $builderUrl = $this->builder->createSession(
            $this->user->user_id,
            $project_id,
            'profile_tab'
        );

        header("Location: {$builderUrl}");
        exit;
    }

    private function getProfileData($user_id)
    {
        // Load profile data from database
        return [];
    }

    private function canEdit(): bool
    {
        // Check permissions
        return true;
    }
}


// ============================================================================
// Example 8: Widget Marketplace Integration
// ============================================================================

/**
 * Widget marketplace with builder-created widgets
 */
class WidgetMarketplace
{
    private $builder;
    private $db;

    public function __construct($builder, $db)
    {
        $this->builder = $builder;
        $this->db = $db;
    }

    /**
     * List available widgets
     */
    public function listWidgets()
    {
        $stmt = $this->db->prepare("
            SELECT
                a.*,
                u.user_name as author_name,
                COUNT(d.id) as installs
            FROM modula_builder_artifacts a
            LEFT JOIN users u ON a.created_by = u.user_id
            LEFT JOIN modula_builder_deployments d ON a.id = d.artifact_id
            WHERE a.type = 'widget'
            AND a.status = 'published'
            GROUP BY a.id
            ORDER BY installs DESC, a.published_at DESC
        ");

        $stmt->execute();
        return $stmt->get_result()->fetch_all(MYSQL_ASSOC);
    }

    /**
     * Install widget to user's page
     */
    public function installWidget($widget_id, $user_id, $page_location)
    {
        // Get widget artifact
        $stmt = $this->db->prepare("
            SELECT * FROM modula_builder_artifacts WHERE id = ?
        ");
        $stmt->bind_param('i', $widget_id);
        $stmt->execute();
        $widget = $stmt->get_result()->fetch_assoc();

        if (!$widget) {
            return false;
        }

        // Create deployment record
        $stmt = $this->db->prepare("
            INSERT INTO modula_builder_deployments (
                artifact_id,
                version,
                environment,
                deployed_to,
                status,
                deployed_by
            ) VALUES (?, ?, 'production', ?, 'active', ?)
        ");

        $stmt->bind_param(
            'issi',
            $widget_id,
            $widget['version'],
            $page_location,
            $user_id
        );

        return $stmt->execute();
    }
}


// ============================================================================
// Example 9: API Endpoints for Frontend
// ============================================================================

/**
 * REST API endpoints
 */
class BuilderAPI
{
    private $builder;

    public function __construct($builder)
    {
        $this->builder = $builder;
    }

    /**
     * GET /api/builder/artifacts/{project_id}
     */
    public function getArtifact($project_id)
    {
        $artifact = $this->builder->getArtifactByProject($project_id);

        header('Content-Type: application/json');

        if ($artifact) {
            echo json_encode([
                'success' => true,
                'artifact' => $artifact
            ]);
        } else {
            http_response_code(404);
            echo json_encode([
                'success' => false,
                'error' => 'Artifact not found'
            ]);
        }
    }

    /**
     * POST /api/builder/create-session
     */
    public function createSession()
    {
        global $user;

        $data = json_decode(file_get_contents('php://input'), true);

        $project_id = $data['project_id'] ?? '';
        $type = $data['type'] ?? 'component';

        if (!$project_id) {
            http_response_code(400);
            echo json_encode(['error' => 'Missing project_id']);
            return;
        }

        $url = $this->builder->createSession(
            $user->user_id,
            $project_id,
            $type
        );

        echo json_encode([
            'success' => true,
            'url' => $url
        ]);
    }
}


// ============================================================================
// Example 10: Smarty Template Functions
// ============================================================================

/**
 * Register Smarty functions for easy template usage
 */
function register_builder_smarty_functions($smarty)
{
    global $builder;

    // {builder_render project="profile_tab_123"}
    $smarty->register_function('builder_render', function($params) use ($builder) {
        $project_id = $params['project'] ?? '';
        if ($project_id) {
            return $builder->renderArtifact($project_id);
        }
        return '';
    });

    // {builder_edit_url project="profile_tab_123"}
    $smarty->register_function('builder_edit_url', function($params) use ($builder) {
        global $user;

        $project_id = $params['project'] ?? '';
        $type = $params['type'] ?? 'component';

        if ($project_id && $user) {
            return $builder->createSession(
                $user->user_id,
                $project_id,
                $type
            );
        }

        return '#';
    });

    // {builder_template project="widget_456"}
    $smarty->register_function('builder_template', function($params) use ($builder) {
        $project_id = $params['project'] ?? '';

        if ($project_id) {
            $path = $builder->getSmartyTemplatePath($project_id);
            if ($path) {
                return basename($path);
            }
        }

        return null;
    });
}

// Usage in templates:
// {builder_render project="profile_tab_123"}
// <a href="{builder_edit_url project="profile_tab_123" type="profile_tab"}">Edit</a>
// {include file="blocks/{builder_template project='widget_456'}"}


// ============================================================================
// Example 11: Version Management
// ============================================================================

/**
 * Manage artifact versions
 */
class VersionManager
{
    private $db;

    public function __construct($db)
    {
        $this->db = $db;
    }

    /**
     * Get version history
     */
    public function getVersionHistory($artifact_id)
    {
        $stmt = $this->db->prepare("
            SELECT
                v.*,
                u.user_name as created_by_name
            FROM modula_builder_versions v
            LEFT JOIN users u ON v.created_by = u.user_id
            WHERE v.artifact_id = ?
            ORDER BY v.created_at DESC
        ");

        $stmt->bind_param('i', $artifact_id);
        $stmt->execute();

        return $stmt->get_result()->fetch_all(MYSQL_ASSOC);
    }

    /**
     * Rollback to previous version
     */
    public function rollback($artifact_id, $version)
    {
        // Get version snapshot
        $stmt = $this->db->prepare("
            SELECT snapshot_json
            FROM modula_builder_versions
            WHERE artifact_id = ? AND version = ?
        ");

        $stmt->bind_param('is', $artifact_id, $version);
        $stmt->execute();
        $result = $stmt->get_result()->fetch_assoc();

        if (!$result) {
            return false;
        }

        // Update artifact to this version
        $stmt = $this->db->prepare("
            UPDATE modula_builder_artifacts
            SET version = ?, mdk_json = ?
            WHERE id = ?
        ");

        $stmt->bind_param(
            'ssi',
            $version,
            $result['snapshot_json'],
            $artifact_id
        );

        return $stmt->execute();
    }
}
