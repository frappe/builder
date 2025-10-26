# Modula Builder Integration

Complete integration package for connecting Modula (Sngine-based platform) with builder.modula.digital (Frappe Builder).

## Overview

This integration enables Modula users to visually create and edit components (Profile Tabs, Widgets, Pages, etc.) using a powerful drag-and-drop builder interface.

```
┌─────────────┐                        ┌──────────────────────┐
│             │   Create/Edit Build    │                      │
│   Modula    │ ──────────────────────>│  builder.modula.     │
│  (Sngine)   │                        │     digital          │
│             │ <──────────────────────│  (Frappe Builder)    │
│             │    Publish Callback    │                      │
└─────────────┘                        └──────────────────────┘
```

## Features

- **Visual Editing**: Drag-and-drop interface for building components
- **Responsive Design**: Mobile, tablet, and desktop breakpoints
- **Version Control**: Track changes and rollback if needed
- **Auto-deployment**: Publish directly to Modula pages
- **Component Library**: Reusable templates and blocks
- **AI Assistance**: Optional AI-powered design suggestions
- **Export Formats**: HTML, MDK JSON, Smarty templates

## Installation

### 1. Database Setup

Apply the database schema to your Modula MySQL database:

```bash
cd modula_integration
mysql -u root -p modula_db < ../builder/modula_database_schema.sql
```

This creates:
- `modula_builder_artifacts` - Published builds
- `modula_builder_versions` - Version history
- `modula_builder_deployments` - Deployment tracking
- `modula_builder_sessions` - Active sessions

### 2. Install PHP Dependencies

```bash
composer require firebase/php-jwt
```

### 3. Configure Modula

Add to your Modula configuration file (e.g., `config.php`):

```php
// Builder Configuration
define('BUILDER_URL', 'https://builder.modula.digital');
define('BUILDER_API_URL', 'https://builder.modula.digital/api/method/builder.modula_api');
define('BUILDER_JWT_SECRET', 'your-shared-secret-key-here');
define('BUILDER_JWT_ALGORITHM', 'HS256');
```

### 4. Include Integration Library

Copy `ModulaBuilderClient.php` to your Modula codebase:

```bash
cp ModulaBuilderClient.php /path/to/modula/includes/
```

### 5. Configure Builder (Frappe)

On the builder.modula.digital server, add to `site_config.json`:

```json
{
  "modula_api_url": "https://modula.digital",
  "modula_jwt_secret": "your-shared-secret-key-here",
  "modula_jwt_algorithm": "HS256",
  "modula_snippets_path": "/var/www/modula/content/snippets",
  "modula_templates_path": "/var/www/modula/content/themes/default/templates/blocks"
}
```

### 6. Create File Directories

On your Modula server:

```bash
mkdir -p /var/www/modula/content/snippets
mkdir -p /var/www/modula/content/themes/default/templates/blocks
chown www-data:www-data /var/www/modula/content/snippets
chown www-data:www-data /var/www/modula/content/themes/default/templates/blocks
```

## Usage

### Basic Example: Edit Profile Tab

```php
<?php
require_once 'includes/ModulaBuilderClient.php';

$builder = new ModulaBuilderClient([
    'builder_url' => BUILDER_URL,
    'jwt_secret' => BUILDER_JWT_SECRET,
    'db' => $db
]);

// When user clicks "Edit Profile Tab"
if (isset($_GET['edit_profile_tab'])) {
    $project_id = "profile_tab_{$user->user_id}";

    $builderUrl = $builder->createSession(
        $user->user_id,
        $project_id,
        'profile_tab'
    );

    redirect($builderUrl);
}

// Render published profile tab
$html = $builder->renderArtifact("profile_tab_{$profile_user->user_id}");
echo $html;
?>
```

### Smarty Template Integration

In your Smarty templates:

```smarty
{* Check if custom profile tab exists *}
{$custom_tab = get_builder_artifact("profile_tab_{$profile_user.user_id}")}

{if $custom_tab}
    {* Render custom tab *}
    {builder_render project="profile_tab_{$profile_user.user_id}"}
{else}
    {* Default profile tab *}
    <div class="default-profile-tab">
        <h1>{$profile_user.user_firstname} {$profile_user.user_lastname}</h1>
    </div>
{/if}

{* Edit button (only for profile owner) *}
{if $user.user_id == $profile_user.user_id}
    <a href="{builder_edit_url project="profile_tab_{$user.user_id}" type="profile_tab"}" class="btn btn-primary">
        Edit Profile Tab
    </a>
{/if}
```

### Handle Publish Callback

Create an API endpoint to receive publish notifications:

```php
// api/builder/callback.php
<?php
require_once '../includes/ModulaBuilderClient.php';

$builder = new ModulaBuilderClient([
    'builder_url' => BUILDER_URL,
    'jwt_secret' => BUILDER_JWT_SECRET,
    'db' => $db
]);

// Get POST data
$data = json_decode(file_get_contents('php://input'), true);

// Handle callback
$response = $builder->handlePublishCallback($data);

// Send response
header('Content-Type: application/json');
echo json_encode($response);
```

## API Reference

### ModulaBuilderClient Methods

#### `createSession(int $userId, string $projectId, string $type, array $options = []): string`

Creates a builder session and returns URL to redirect user to.

**Parameters:**
- `$userId` - Modula user ID
- `$projectId` - Unique project identifier
- `$type` - Build type: `profile_tab`, `widget`, `page`, `component`, `layout`, `card`
- `$options` - Optional:
  - `permissions` - Array of permissions (default: `['edit', 'publish']`)
  - `expires_in` - Token expiration in seconds (default: `3600`)

**Returns:** URL string to redirect user to builder

**Example:**
```php
$url = $builder->createSession(
    $user->user_id,
    'widget_pricing_card',
    'widget',
    ['expires_in' => 7200]
);
```

#### `handlePublishCallback(array $data): array`

Handles publish notification from builder.

**Parameters:**
- `$data` - POST data from builder containing:
  - `project_id`
  - `build_code`
  - `version`
  - `artifacts` - Paths to generated files

**Returns:** Response array with `success` and `artifact_id`

#### `renderArtifact(string $projectId): string`

Gets HTML fragment for rendering in your pages.

**Parameters:**
- `$projectId` - Project identifier

**Returns:** HTML string

**Example:**
```php
echo $builder->renderArtifact('profile_tab_123');
```

#### `getArtifactByProject(string $projectId): ?array`

Gets full artifact data from database.

**Parameters:**
- `$projectId` - Project identifier

**Returns:** Array with artifact data or `null` if not found

#### `getSmartyTemplatePath(string $projectId): ?string`

Gets path to Smarty template file.

**Parameters:**
- `$projectId` - Project identifier

**Returns:** Path string or `null`

**Example:**
```php
$tplPath = $builder->getSmartyTemplatePath('widget_456');
if ($tplPath) {
    $smarty->display($tplPath);
}
```

#### `exportBuild(string $pageName, string $format, array $options): array`

Exports a build programmatically via API.

**Parameters:**
- `$pageName` - Builder page name
- `$format` - Export format: `html`, `json`, `tpl`, or `all`
- `$options` - Export options:
  - `minify` - Minify output (default: `false`)
  - `inline_css` - Inline critical CSS (default: `true`)
  - `scoped` - Use scoped styles (default: `true`)

**Returns:** Array with exported content

#### `publishBuild(string $pageName, string $version, string $callbackUrl, array $options): array`

Publishes a build programmatically.

**Parameters:**
- `$pageName` - Builder page name
- `$version` - Version string (e.g., "1.0.1")
- `$callbackUrl` - URL to send callback to
- `$options` - Publish options

**Returns:** Publish result array

## Workflow

### 1. User Opens Builder

```php
// In Modula controller
$builderUrl = $builder->createSession(
    $user->user_id,
    'profile_tab_123',
    'profile_tab'
);

redirect($builderUrl);
```

### 2. Builder Opens

- User is redirected to `https://builder.modula.digital/app/builder?token=...&project=profile_tab_123`
- Builder validates JWT token
- Loads existing build or creates new one
- User edits visually

### 3. User Publishes

- User clicks "Publish" in builder
- Builder generates:
  - HTML fragment (clean, injectable)
  - MDK JSON (re-editable schema)
  - Smarty template (optional)
- Saves to file system
- Sends callback to Modula

### 4. Modula Receives Callback

```php
// Callback handler receives:
{
  "project_id": "profile_tab_123",
  "build_code": "b_abc123def",
  "version": "1.0.1",
  "artifacts": {
    "html_fragment": "/content/snippets/profile_tab_123/1.0.1/fragment.html",
    "mdk_json": "/content/snippets/profile_tab_123/1.0.1/build.mdk.json",
    "smarty_tpl": "/content/themes/default/templates/blocks/profile_tab_profile_tab_123.tpl"
  }
}

// Modula stores in database
// Clears cache
// Notifies user
```

### 5. Rendering on Profile Page

```php
// In profile page
$html = $builder->renderArtifact('profile_tab_123');
echo $html;
```

## File Structure

```
/var/www/modula/
├── content/
│   ├── snippets/                    # Builder artifacts
│   │   ├── profile_tab_123/
│   │   │   ├── latest/              # Symlink to latest version
│   │   │   │   ├── fragment.html
│   │   │   │   ├── build.mdk.json
│   │   │   │   └── metadata.json
│   │   │   ├── 1.0.0/
│   │   │   │   ├── fragment.html
│   │   │   │   └── build.mdk.json
│   │   │   └── 1.0.1/
│   │   │       ├── fragment.html
│   │   │       └── build.mdk.json
│   │   └── widget_456/
│   │       └── ...
│   └── themes/
│       └── default/
│           └── templates/
│               └── blocks/          # Smarty templates
│                   ├── profile_tab_profile_tab_123.tpl
│                   └── widget_widget_456.tpl
└── includes/
    └── ModulaBuilderClient.php      # Integration library
```

## Version Control

### Viewing Version History

```php
$versionManager = new VersionManager($db);
$history = $versionManager->getVersionHistory($artifact_id);

foreach ($history as $version) {
    echo "Version {$version['version']} - {$version['created_at']}\n";
    echo "By: {$version['created_by_name']}\n";
    echo "Changes: {$version['change_summary']}\n";
}
```

### Rolling Back

```php
// Rollback to version 1.0.0
$versionManager->rollback($artifact_id, '1.0.0');
```

## Advanced Usage

### Custom Builder Client with Hooks

```php
class MyBuilderClient extends ModulaBuilderClient
{
    protected function onPublish(
        string $projectId,
        string $buildCode,
        string $version,
        int $artifactId
    ): void {
        // Clear cache
        cache_delete("build_{$projectId}");

        // Send notification
        $this->notifyOwner($projectId, "Build published: v{$version}");

        // Log to analytics
        analytics_track('builder_publish', [
            'project_id' => $projectId,
            'version' => $version
        ]);

        // Auto-deploy to production
        if (config('auto_deploy_enabled')) {
            $this->deployToProduction($artifactId);
        }
    }

    private function deployToProduction(int $artifactId)
    {
        // Your deployment logic
    }
}
```

### Widget Marketplace

```php
$marketplace = new WidgetMarketplace($builder, $db);

// List all widgets
$widgets = $marketplace->listWidgets();

// Install widget to user's page
$marketplace->installWidget(
    $widget_id,
    $user->user_id,
    'sidebar_right'
);
```

## Security

### JWT Token Security

- Tokens expire after 1 hour (configurable)
- Use strong secret key (min 256 bits for HS256)
- For production, consider using RS256 (RSA) instead of HS256
- Validate all incoming tokens

### File System Security

- Store artifacts outside webroot when possible
- Use proper file permissions (644 for files, 755 for directories)
- Sanitize HTML output before rendering
- Implement access control on artifact URLs

### Database Security

- Use prepared statements (already implemented)
- Validate user permissions before allowing edits
- Audit publish actions
- Regular backups

## Troubleshooting

### "Token validation failed"

**Cause:** JWT secret mismatch between Modula and Builder

**Solution:**
1. Check both `BUILDER_JWT_SECRET` in Modula config
2. Check `modula_jwt_secret` in Builder site_config.json
3. Ensure they match exactly

### "Artifact not found"

**Cause:** Build hasn't been published yet or wrong project_id

**Solution:**
1. Check if build exists in `modula_builder_artifacts` table
2. Verify project_id matches
3. Check if status is 'published'

### "Permission denied" on file write

**Cause:** Web server doesn't have write access to directories

**Solution:**
```bash
chown -R www-data:www-data /var/www/modula/content/snippets
chown -R www-data:www-data /var/www/modula/content/themes/default/templates/blocks
chmod -R 755 /var/www/modula/content/snippets
```

### Callback not received

**Cause:** Network issue or incorrect callback URL

**Solution:**
1. Check builder logs: `bench --site builder.modula.digital console`
2. Verify callback URL is accessible from builder server
3. Check firewall rules

## Performance Optimization

### Caching

```php
// Cache rendered artifacts
$cache_key = "artifact_{$project_id}";
$html = cache_get($cache_key);

if (!$html) {
    $html = $builder->renderArtifact($project_id);
    cache_set($cache_key, $html, 3600); // 1 hour
}

echo $html;
```

### Database Indexes

Indexes are already created by the schema, but verify:

```sql
SHOW INDEXES FROM modula_builder_artifacts;
```

### CDN Integration

For static artifacts, consider serving from CDN:

```php
$cdnUrl = "https://cdn.modula.digital/snippets/{$project_id}/latest/fragment.html";
```

## Testing

See `example_usage.php` for comprehensive examples of all integration patterns.

### Manual Testing

1. Open builder session:
   ```php
   $url = $builder->createSession(1, 'test_project', 'widget');
   echo $url;
   ```

2. Edit in builder UI

3. Click "Publish"

4. Check database:
   ```sql
   SELECT * FROM modula_builder_artifacts WHERE project_id = 'test_project';
   ```

5. Render artifact:
   ```php
   echo $builder->renderArtifact('test_project');
   ```

## Support

For issues or questions:
- Check logs: `/var/log/nginx/error.log` or `/var/www/modula/logs/`
- Builder logs: `bench --site builder.modula.digital logs`
- Database logs: `SHOW ENGINE INNODB STATUS`

## License

Proprietary - Modula Digital

## Changelog

### Version 1.0.0 (2025-10-26)
- Initial release
- JWT authentication
- Export to HTML, MDK JSON, Smarty templates
- Version control
- Publish callbacks
- Database schema
