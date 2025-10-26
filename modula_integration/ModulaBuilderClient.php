<?php

/**
 * Modula Builder Client
 * PHP integration library for communicating with builder.modula.digital
 *
 * Usage in Modula (Sngine):
 *
 *   require_once 'ModulaBuilderClient.php';
 *
 *   $builder = new ModulaBuilderClient([
 *       'builder_url' => 'https://builder.modula.digital',
 *       'jwt_secret' => 'your-secret-key',
 *       'db' => $db  // Sngine database connection
 *   ]);
 *
 *   // Open builder for editing
 *   $url = $builder->createSession($user->user_id, $project_id, 'profile_tab');
 *   redirect($url);
 *
 *   // Handle publish callback
 *   $builder->handlePublishCallback($_POST);
 */

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

class ModulaBuilderClient
{
    private $builderUrl;
    private $jwtSecret;
    private $jwtAlgorithm;
    private $db;
    private $apiEndpoint;

    /**
     * Constructor
     *
     * @param array $config Configuration options
     *   - builder_url: Base URL of builder.modula.digital
     *   - jwt_secret: Shared secret for JWT signing
     *   - jwt_algorithm: Algorithm (default: HS256)
     *   - db: Database connection object
     */
    public function __construct(array $config)
    {
        $this->builderUrl = rtrim($config['builder_url'], '/');
        $this->jwtSecret = $config['jwt_secret'];
        $this->jwtAlgorithm = $config['jwt_algorithm'] ?? 'HS256';
        $this->db = $config['db'];
        $this->apiEndpoint = $this->builderUrl . '/api/method/builder.modula_api';
    }

    /**
     * Create a builder session and return URL to open builder
     *
     * @param int $userId Sngine user ID
     * @param string $projectId Project identifier
     * @param string $type Build type (profile_tab, widget, page, etc.)
     * @param array $options Additional options
     * @return string URL to redirect user to
     */
    public function createSession(
        int $userId,
        string $projectId,
        string $type = 'component',
        array $options = []
    ): string {
        // Create JWT token
        $token = $this->createJWT($userId, $projectId, $type, $options);

        // Build URL
        $params = http_build_query([
            'token' => $token,
            'project' => $projectId
        ]);

        return "{$this->builderUrl}/app/builder?{$params}";
    }

    /**
     * Create JWT token for builder authentication
     *
     * @param int $userId
     * @param string $projectId
     * @param string $type
     * @param array $options
     * @return string JWT token
     */
    public function createJWT(
        int $userId,
        string $projectId,
        string $type,
        array $options = []
    ): string {
        $now = time();

        $payload = [
            'iss' => $_SERVER['HTTP_HOST'] ?? 'modula.digital',
            'aud' => 'builder.modula.digital',
            'sub' => (string) $userId,
            'project_id' => $projectId,
            'type' => $type,
            'permissions' => $options['permissions'] ?? ['edit', 'publish'],
            'iat' => $now,
            'exp' => $now + ($options['expires_in'] ?? 3600) // 1 hour default
        ];

        return JWT::encode($payload, $this->jwtSecret, $this->jwtAlgorithm);
    }

    /**
     * Validate JWT token from builder
     *
     * @param string $token
     * @return array|null Decoded payload or null if invalid
     */
    public function validateJWT(string $token): ?array
    {
        try {
            $decoded = JWT::decode(
                $token,
                new Key($this->jwtSecret, $this->jwtAlgorithm)
            );

            return (array) $decoded;
        } catch (\Exception $e) {
            error_log("JWT validation error: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Handle publish callback from builder
     *
     * @param array $data POST data from builder
     * @return array Response data
     */
    public function handlePublishCallback(array $data): array
    {
        // Validate Authorization header
        $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        $token = str_replace('Bearer ', '', $authHeader);

        if (!$this->validateJWT($token)) {
            http_response_code(401);
            return ['error' => 'Unauthorized'];
        }

        // Extract data
        $projectId = $data['project_id'] ?? '';
        $buildCode = $data['build_code'] ?? '';
        $version = $data['version'] ?? '1.0.0';
        $artifacts = $data['artifacts'] ?? [];

        if (!$projectId || !$buildCode) {
            http_response_code(400);
            return ['error' => 'Missing required fields'];
        }

        // Store in database
        $artifactId = $this->storeArtifacts($projectId, $buildCode, $version, $artifacts, $data);

        // Trigger any post-publish hooks
        $this->onPublish($projectId, $buildCode, $version, $artifactId);

        return [
            'success' => true,
            'artifact_id' => $artifactId,
            'message' => 'Build published successfully'
        ];
    }

    /**
     * Store artifacts in database
     *
     * @param string $projectId
     * @param string $buildCode
     * @param string $version
     * @param array $artifacts Artifact file paths
     * @param array $data Full callback data
     * @return int Artifact ID
     */
    private function storeArtifacts(
        string $projectId,
        string $buildCode,
        string $version,
        array $artifacts,
        array $data
    ): int {
        // Load artifact contents from files
        $htmlFragment = $this->loadFileContent($artifacts['html_fragment'] ?? '');
        $mdkJson = $this->loadFileContent($artifacts['mdk_json'] ?? '');
        $smartyTpl = $this->loadFileContent($artifacts['smarty_tpl'] ?? '');

        // Check if artifact already exists
        $stmt = $this->db->prepare(
            "SELECT id FROM modula_builder_artifacts WHERE build_code = ?"
        );
        $stmt->bind_param('s', $buildCode);
        $stmt->execute();
        $result = $stmt->get_result();
        $existing = $result->fetch_assoc();

        if ($existing) {
            // Update existing artifact
            $stmt = $this->db->prepare("
                UPDATE modula_builder_artifacts
                SET
                    version = ?,
                    html_fragment = ?,
                    html_path = ?,
                    mdk_json = ?,
                    mdk_path = ?,
                    smarty_tpl = ?,
                    smarty_path = ?,
                    status = 'published',
                    published_at = NOW(),
                    updated_at = NOW()
                WHERE build_code = ?
            ");

            $stmt->bind_param(
                'ssssssss',
                $version,
                $htmlFragment,
                $artifacts['html_fragment'],
                $mdkJson,
                $artifacts['mdk_json'],
                $smartyTpl,
                $artifacts['smarty_tpl'],
                $buildCode
            );

            $stmt->execute();
            $artifactId = $existing['id'];
        } else {
            // Insert new artifact
            $stmt = $this->db->prepare("
                INSERT INTO modula_builder_artifacts (
                    project_id,
                    build_code,
                    version,
                    type,
                    name,
                    html_fragment,
                    html_path,
                    mdk_json,
                    mdk_path,
                    smarty_tpl,
                    smarty_path,
                    created_by,
                    status,
                    published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', NOW())
            ");

            $type = $data['type'] ?? 'component';
            $name = $data['name'] ?? "Build {$buildCode}";
            $userId = $this->getUserIdFromToken($data);

            $stmt->bind_param(
                'sssssssssssi',
                $projectId,
                $buildCode,
                $version,
                $type,
                $name,
                $htmlFragment,
                $artifacts['html_fragment'],
                $mdkJson,
                $artifacts['mdk_json'],
                $smartyTpl,
                $artifacts['smarty_tpl'],
                $userId
            );

            $stmt->execute();
            $artifactId = $stmt->insert_id;
        }

        // Create version snapshot
        $this->createVersionSnapshot($artifactId, $version, $mdkJson);

        return $artifactId;
    }

    /**
     * Create version snapshot
     *
     * @param int $artifactId
     * @param string $version
     * @param string $snapshotJson
     */
    private function createVersionSnapshot(
        int $artifactId,
        string $version,
        string $snapshotJson
    ): void {
        $stmt = $this->db->prepare("
            INSERT INTO modula_builder_versions (
                artifact_id,
                version,
                snapshot_json,
                change_summary,
                created_by
            ) VALUES (?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE
                snapshot_json = VALUES(snapshot_json)
        ");

        $changeSummary = "Published version {$version}";
        $userId = 1; // System user - update if needed

        $stmt->bind_param(
            'isssi',
            $artifactId,
            $version,
            $snapshotJson,
            $changeSummary,
            $userId
        );

        $stmt->execute();
    }

    /**
     * Load file content
     *
     * @param string $path
     * @return string
     */
    private function loadFileContent(string $path): string
    {
        if (empty($path)) {
            return '';
        }

        // Remove leading slash for local file access
        $localPath = ltrim($path, '/');

        if (file_exists($localPath)) {
            return file_get_contents($localPath);
        }

        return '';
    }

    /**
     * Get user ID from token in request
     *
     * @param array $data
     * @return int
     */
    private function getUserIdFromToken(array $data): int
    {
        $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        $token = str_replace('Bearer ', '', $authHeader);

        $payload = $this->validateJWT($token);

        if ($payload && isset($payload['sub'])) {
            return (int) $payload['sub'];
        }

        return 1; // Default to system user
    }

    /**
     * Get artifact by project ID
     *
     * @param string $projectId
     * @return array|null
     */
    public function getArtifactByProject(string $projectId): ?array
    {
        $stmt = $this->db->prepare("
            SELECT *
            FROM modula_builder_artifacts
            WHERE project_id = ?
            AND status IN ('published', 'draft')
            ORDER BY updated_at DESC
            LIMIT 1
        ");

        $stmt->bind_param('s', $projectId);
        $stmt->execute();
        $result = $stmt->get_result();

        return $result->fetch_assoc();
    }

    /**
     * Get artifact HTML for rendering
     *
     * @param string $projectId
     * @return string HTML fragment
     */
    public function renderArtifact(string $projectId): string
    {
        $artifact = $this->getArtifactByProject($projectId);

        if (!$artifact) {
            return "<!-- No artifact found for project {$projectId} -->";
        }

        // Return HTML fragment (from DB or load from file)
        if (!empty($artifact['html_fragment'])) {
            return $artifact['html_fragment'];
        }

        if (!empty($artifact['html_path'])) {
            return $this->loadFileContent($artifact['html_path']);
        }

        return "<!-- Artifact found but no HTML content -->";
    }

    /**
     * Get Smarty template path for inclusion
     *
     * @param string $projectId
     * @return string|null Template path or null
     */
    public function getSmartyTemplatePath(string $projectId): ?string
    {
        $artifact = $this->getArtifactByProject($projectId);

        if ($artifact && !empty($artifact['smarty_path'])) {
            return $artifact['smarty_path'];
        }

        return null;
    }

    /**
     * Export build from builder
     *
     * @param string $pageName Builder page name
     * @param string $format Export format (html, json, tpl, all)
     * @param array $options Export options
     * @return array Export data
     */
    public function exportBuild(
        string $pageName,
        string $format = 'all',
        array $options = []
    ): array {
        $url = $this->apiEndpoint . '.export_build';

        $response = $this->callBuilderAPI($url, [
            'page_name' => $pageName,
            'format' => $format,
            'options' => json_encode($options)
        ]);

        return json_decode($response, true);
    }

    /**
     * Publish build via API
     *
     * @param string $pageName
     * @param string $version
     * @param string $callbackUrl
     * @param array $options
     * @return array
     */
    public function publishBuild(
        string $pageName,
        string $version = null,
        string $callbackUrl = null,
        array $options = []
    ): array {
        $url = $this->apiEndpoint . '.publish_build';

        $response = $this->callBuilderAPI($url, [
            'page_name' => $pageName,
            'version' => $version,
            'callback_url' => $callbackUrl,
            'options' => json_encode($options)
        ]);

        return json_decode($response, true);
    }

    /**
     * Call Builder API
     *
     * @param string $url
     * @param array $data
     * @return string Response body
     */
    private function callBuilderAPI(string $url, array $data): string
    {
        $ch = curl_init($url);

        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Accept: application/json'
            ]
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        if ($httpCode !== 200) {
            error_log("Builder API error: HTTP {$httpCode}");
        }

        curl_close($ch);

        return $response;
    }

    /**
     * Hook: Called after successful publish
     * Override this in child class to add custom behavior
     *
     * @param string $projectId
     * @param string $buildCode
     * @param string $version
     * @param int $artifactId
     */
    protected function onPublish(
        string $projectId,
        string $buildCode,
        string $version,
        int $artifactId
    ): void {
        // Override in child class for custom logic
        // Examples:
        // - Clear cache
        // - Send notifications
        // - Trigger deployment
        // - Update related records
    }
}
