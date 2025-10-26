<?php

/**
 * Modula Builder Client - Shared Hosting Version
 * PHP integration library for communicating with builder.modula.digital
 *
 * Optimized for shared hosting environments with limited permissions
 *
 * Usage in Modula (Sngine):
 *
 *   require_once __DIR__ . '/includes/builder/ModulaBuilderClient.php';
 *
 *   $builder = new ModulaBuilderClient([
 *       'builder_url' => 'https://builder.modula.digital',
 *       'jwt_secret' => 'your-secret-key',
 *       'db' => $db
 *   ]);
 */

class ModulaBuilderClient
{
    private $builderUrl;
    private $jwtSecret;
    private $jwtAlgorithm;
    private $db;
    private $apiEndpoint;
    private $basePath;
    private $useComposer;

    /**
     * Constructor
     *
     * @param array $config Configuration options
     */
    public function __construct(array $config)
    {
        $this->builderUrl = rtrim($config['builder_url'], '/');
        $this->jwtSecret = $config['jwt_secret'];
        $this->jwtAlgorithm = $config['jwt_algorithm'] ?? 'HS256';
        $this->db = $config['db'];
        $this->basePath = $config['base_path'] ?? dirname(dirname(__DIR__));
        $this->apiEndpoint = $this->builderUrl . '/api/method/builder.modula_api';

        // Check if firebase/php-jwt is available via Composer
        $this->useComposer = file_exists($this->basePath . '/vendor/autoload.php');

        if (!$this->useComposer) {
            // Use fallback JWT implementation
            require_once __DIR__ . '/jwt_fallback.php';
        }
    }

    /**
     * Create a builder session and return URL to open builder
     */
    public function createSession(
        int $userId,
        string $projectId,
        string $type = 'component',
        array $options = []
    ): string {
        $token = $this->createJWT($userId, $projectId, $type, $options);

        $params = http_build_query([
            'token' => $token,
            'project' => $projectId
        ]);

        return "{$this->builderUrl}/app/builder?{$params}";
    }

    /**
     * Create JWT token - Shared hosting compatible
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
            'exp' => $now + ($options['expires_in'] ?? 3600)
        ];

        if ($this->useComposer) {
            // Use firebase/php-jwt
            require_once $this->basePath . '/vendor/autoload.php';
            return \Firebase\JWT\JWT::encode($payload, $this->jwtSecret, $this->jwtAlgorithm);
        } else {
            // Use fallback implementation
            return JWT_Fallback::encode($payload, $this->jwtSecret, $this->jwtAlgorithm);
        }
    }

    /**
     * Validate JWT token
     */
    public function validateJWT(string $token): ?array
    {
        try {
            if ($this->useComposer) {
                require_once $this->basePath . '/vendor/autoload.php';
                $decoded = \Firebase\JWT\JWT::decode(
                    $token,
                    new \Firebase\JWT\Key($this->jwtSecret, $this->jwtAlgorithm)
                );
                return (array) $decoded;
            } else {
                return JWT_Fallback::decode($token, $this->jwtSecret, $this->jwtAlgorithm);
            }
        } catch (\Exception $e) {
            error_log("JWT validation error: " . $e->getMessage());
            return null;
        }
    }

    /**
     * Handle publish callback from builder
     */
    public function handlePublishCallback(array $data): array
    {
        // Validate Authorization header
        $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
        $token = str_replace('Bearer ', '', $authHeader);

        if (!$this->validateJWT($token)) {
            http_response_code(401);
            return ['error' => 'Unauthorized'];
        }

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

        // Trigger hooks
        $this->onPublish($projectId, $buildCode, $version, $artifactId);

        return [
            'success' => true,
            'artifact_id' => $artifactId,
            'message' => 'Build published successfully'
        ];
    }

    /**
     * Store artifacts in database - Shared hosting compatible
     */
    private function storeArtifacts(
        string $projectId,
        string $buildCode,
        string $version,
        array $artifacts,
        array $data
    ): int {
        // Use relative paths for shared hosting
        $snippetsPath = $this->getRelativePath($artifacts['html_fragment'] ?? '');
        $mdkPath = $this->getRelativePath($artifacts['mdk_json'] ?? '');
        $tplPath = $this->getRelativePath($artifacts['smarty_tpl'] ?? '');

        // Load artifact contents
        $htmlFragment = $this->loadFileContent($snippetsPath);
        $mdkJson = $this->loadFileContent($mdkPath);
        $smartyTpl = $this->loadFileContent($tplPath);

        // Check if artifact exists
        $stmt = $this->db->prepare(
            "SELECT id FROM modula_builder_artifacts WHERE build_code = ?"
        );
        $stmt->bind_param('s', $buildCode);
        $stmt->execute();
        $result = $stmt->get_result();
        $existing = $result->fetch_assoc();

        if ($existing) {
            // Update existing
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
                $snippetsPath,
                $mdkJson,
                $mdkPath,
                $smartyTpl,
                $tplPath,
                $buildCode
            );

            $stmt->execute();
            $artifactId = $existing['id'];
        } else {
            // Insert new
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
                $snippetsPath,
                $mdkJson,
                $mdkPath,
                $smartyTpl,
                $tplPath,
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
     * Get relative path for shared hosting
     */
    private function getRelativePath(string $path): string
    {
        if (empty($path)) {
            return '';
        }

        // Remove leading slash and absolute paths
        $path = ltrim($path, '/');

        // Convert /content/... to relative path
        if (strpos($path, 'content/') === 0) {
            return $path;
        }

        return $path;
    }

    /**
     * Load file content - Shared hosting compatible
     */
    private function loadFileContent(string $path): string
    {
        if (empty($path)) {
            return '';
        }

        // Try relative to base path
        $fullPath = $this->basePath . '/' . ltrim($path, '/');

        if (file_exists($fullPath) && is_readable($fullPath)) {
            return file_get_contents($fullPath);
        }

        // Try relative to current directory
        if (file_exists($path) && is_readable($path)) {
            return file_get_contents($path);
        }

        return '';
    }

    /**
     * Create version snapshot
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
        $userId = 1;

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
     * Get user ID from token
     */
    private function getUserIdFromToken(array $data): int
    {
        $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
        $token = str_replace('Bearer ', '', $authHeader);

        $payload = $this->validateJWT($token);

        if ($payload && isset($payload['sub'])) {
            return (int) $payload['sub'];
        }

        return 1;
    }

    /**
     * Get artifact by project ID
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
     */
    public function renderArtifact(string $projectId): string
    {
        $artifact = $this->getArtifactByProject($projectId);

        if (!$artifact) {
            return "<!-- No artifact found for project {$projectId} -->";
        }

        // Return from DB first (faster)
        if (!empty($artifact['html_fragment'])) {
            return $artifact['html_fragment'];
        }

        // Fallback to file
        if (!empty($artifact['html_path'])) {
            return $this->loadFileContent($artifact['html_path']);
        }

        return "<!-- Artifact found but no HTML content -->";
    }

    /**
     * Get Smarty template path
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
     * Call Builder API - Shared hosting compatible
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
            ],
            CURLOPT_TIMEOUT => 30,
            CURLOPT_FOLLOWLOCATION => true
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        if ($httpCode !== 200) {
            error_log("Builder API error: HTTP {$httpCode}");
        }

        curl_close($ch);

        return $response ?: '';
    }

    /**
     * Hook: Called after successful publish
     */
    protected function onPublish(
        string $projectId,
        string $buildCode,
        string $version,
        int $artifactId
    ): void {
        // Override in child class
    }
}
