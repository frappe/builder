# Modula Builder - Quick Start Guide

This guide will get you up and running with Modula Builder in minutes.

## What is Modula Builder?

Modula Builder is a visual drag-and-drop interface that allows Modula users to create custom Profile Tabs, Widgets, Pages, and Components without writing code. It's built on Frappe Builder and seamlessly integrates with your Modula platform.

## Architecture Overview

```
Modula (modula.digital)          builder.modula.digital
      ↓                                    ↓
User clicks "Edit"              Opens visual editor
      ↓                                    ↓
Creates JWT token               User designs component
      ↓                                    ↓
Redirects to builder            User clicks "Publish"
      ↓                                    ↓
                    ← Callback with artifacts ←
      ↓
Stores in database
      ↓
Renders on page
```

## Prerequisites

### Builder Server
- Linux server (Ubuntu 20.04+ recommended)
- Python 3.10+
- Frappe Framework installed
- Domain: builder.modula.digital

### Modula Server
- PHP 8.0+
- MySQL/MariaDB
- Sngine platform running
- Domain: modula.digital

## Installation

### Step 1: Clone Repository

```bash
cd ~/
git clone https://github.com/Modula-Digital/builder.git
cd builder
git checkout claude/create-modula-builder-011CUUj7xJRRSdAdrAa9L4zr
```

### Step 2: Deploy Builder Side

On your builder.modula.digital server:

```bash
cd modula_integration
chmod +x deploy_builder.sh
./deploy_builder.sh
```

Follow the prompts to configure:
- Modula API URL (e.g., `https://modula.digital`)
- JWT Secret (create a strong 32+ character secret)
- JWT Algorithm (use `HS256` for simplicity)
- File paths for snippets and templates

### Step 3: Deploy Modula Side

On your modula.digital server:

```bash
# Copy integration files
scp -r modula_integration root@modula.digital:/tmp/

# SSH into Modula server
ssh root@modula.digital

# Run deployment
cd /tmp/modula_integration
chmod +x deploy_modula.sh
./deploy_modula.sh
```

Follow the prompts (use the **same JWT secret** as Step 2).

### Step 4: Configure Modula Code

Add to your Modula initialization file (e.g., `includes/init.php`):

```php
// Load builder functions
require_once __DIR__ . '/builder_functions.php';
```

After Smarty initialization:

```php
// Register builder Smarty functions
require_once __DIR__ . '/builder_smarty.php';
```

### Step 5: Test Integration

Create a test file `test_builder.php`:

```php
<?php
require_once 'includes/config.php';
require_once 'includes/builder_functions.php';

// Test: Create builder session
$builderUrl = open_builder_session(
    $user->user_id,
    'test_project_001',
    'widget'
);

echo "Builder URL: " . $builderUrl . "\n";

// Redirect user
// header("Location: $builderUrl");
```

Run it:
```bash
php test_builder.php
```

You should get a URL like:
```
https://builder.modula.digital/app/builder?token=eyJ...&project=test_project_001
```

## Basic Usage

### 1. Open Builder from Modula

```php
// In your controller
function edit_profile_tab() {
    global $user;

    $project_id = "profile_tab_{$user->user_id}";

    $url = open_builder_session(
        $user->user_id,
        $project_id,
        'profile_tab'
    );

    redirect($url);
}
```

### 2. Add "Edit" Button in Smarty Template

```smarty
{* profile.tpl *}
<div class="profile-header">
    <h1>{$profile_user.user_firstname} {$profile_user.user_lastname}</h1>

    {* Show edit button if viewing own profile *}
    {if $user.user_id == $profile_user.user_id}
        <a href="{builder_edit_url project="profile_tab_{$user.user_id}" type="profile_tab"}"
           class="btn btn-primary">
            <i class="fa fa-edit"></i> Customize Profile
        </a>
    {/if}
</div>
```

### 3. Render Published Component

```smarty
{* Check if custom profile tab exists *}
{if builder_exists project="profile_tab_{$profile_user.user_id}"}
    {* Render custom tab *}
    {builder_render project="profile_tab_{$profile_user.user_id}"}
{else}
    {* Default profile content *}
    <div class="default-profile">
        <!-- Default profile HTML -->
    </div>
{/if}
```

### 4. PHP Rendering

```php
// Get artifact HTML
$html = render_builder_artifact("profile_tab_{$user_id}");

if ($html) {
    echo $html;
} else {
    echo "<!-- No custom profile tab -->";
}
```

## Workflow Example

### Creating a Custom Profile Tab

1. **User clicks "Customize Profile"** in Modula
   - Modula creates JWT token
   - Redirects to `builder.modula.digital`

2. **User edits in Builder**
   - Drag-and-drop components
   - Style with visual controls
   - Preview responsive breakpoints
   - Add dynamic variables (e.g., `{{user.name}}`)

3. **User clicks "Publish"**
   - Builder generates:
     - Clean HTML fragment
     - MDK JSON schema
     - Smarty template
   - Stores files in `/content/snippets/`
   - Sends callback to Modula

4. **Modula receives callback**
   - Stores in `modula_builder_artifacts` table
   - Clears cache
   - Component is now live

5. **Component appears on profile page**
   - Smarty function renders HTML
   - Fully responsive
   - Can be re-edited anytime

## Common Use Cases

### Profile Tabs

```php
$project_id = "profile_tab_{$user_id}";
$url = open_builder_session($user_id, $project_id, 'profile_tab');
```

### Widgets

```php
$project_id = "widget_latest_posts";
$url = open_builder_session($user_id, $project_id, 'widget');
```

### Custom Pages

```php
$project_id = "page_about_me";
$url = open_builder_session($user_id, $project_id, 'page');
```

### Reusable Components

```php
$project_id = "component_header_nav";
$url = open_builder_session($user_id, $project_id, 'component');
```

## Dynamic Variables

Builder supports dynamic variables using `{{variable}}` syntax:

```html
<!-- In Builder -->
<h1>{{user.name}}</h1>
<img src="{{user.avatar}}" alt="{{user.name}}" />
```

Variables are automatically converted to Smarty syntax on export:

```smarty
<!-- Exported Smarty template -->
<h1>{$user->_data.user_firstname} {$user->_data.user_lastname}</h1>
<img src="{$user->_data.user_picture}" alt="{$user->_data.user_firstname}" />
```

## API Endpoints

### Builder API (builder.modula.digital)

- `POST /api/method/builder.modula_api.validate_token` - Validate JWT
- `POST /api/method/builder.modula_api.export_build` - Export build
- `POST /api/method/builder.modula_api.publish_build` - Publish build
- `POST /api/method/builder.modula_api.import_from_mdk` - Import from JSON

### Modula API (modula.digital)

- `POST /api/builder/callback.php` - Receive publish callback

## Troubleshooting

### "Token validation failed"

**Solution:** Ensure JWT secrets match on both sides:
```bash
# On Builder server
bench --site builder.modula.digital config modula_jwt_secret

# On Modula server
grep BUILDER_JWT_SECRET /var/www/modula/includes/config.php
```

### "Permission denied" on file write

**Solution:** Fix permissions:
```bash
chown -R www-data:www-data /var/www/modula/content/snippets
chmod -R 755 /var/www/modula/content/snippets
```

### Callback not received

**Solution:** Check firewall and test manually:
```bash
curl -X POST https://modula.digital/api/builder/callback.php \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Component not rendering

**Solution:** Check database:
```sql
SELECT * FROM modula_builder_artifacts WHERE project_id = 'your_project_id';
```

## Files Reference

### Created on Builder Server
- `/home/frappe/frappe-bench/apps/builder/builder/modula_api.py` - API endpoints
- `/home/frappe/frappe-bench/apps/builder/builder/modula_database_schema.sql` - Database schema
- `/home/frappe/frappe-bench/apps/builder/builder/fixtures/custom_fields.json` - Custom fields

### Created on Modula Server
- `/var/www/modula/includes/builder/ModulaBuilderClient.php` - Integration client
- `/var/www/modula/includes/builder_functions.php` - Helper functions
- `/var/www/modula/includes/builder_smarty.php` - Smarty functions
- `/var/www/modula/api/builder/callback.php` - Callback endpoint
- `/var/www/modula/content/snippets/` - Published artifacts
- `/var/www/modula/content/themes/default/templates/blocks/` - Smarty templates

### Database Tables (Modula)
- `modula_builder_artifacts` - Published builds
- `modula_builder_versions` - Version history
- `modula_builder_deployments` - Deployment tracking
- `modula_builder_sessions` - Active sessions

## Next Steps

1. **Customize Builder Interface** - Add custom blocks and templates
2. **Create Widget Marketplace** - Let users share/sell widgets
3. **Add AI Features** - Integrate AI-powered design suggestions
4. **Build Component Library** - Pre-built professional templates
5. **Analytics** - Track widget usage and performance

## Support

For detailed documentation:
- `MODULA_INTEGRATION.md` - Complete architecture guide
- `modula_integration/README.md` - Integration manual
- `modula_integration/example_usage.php` - Code examples

## Security Notes

- Keep JWT secret secure (32+ characters)
- Use HTTPS for all communication
- Regularly backup database
- Update dependencies regularly
- Validate all user inputs

## Performance Tips

- Cache rendered artifacts (1 hour)
- Use CDN for static assets
- Enable Gzip compression
- Optimize database indexes
- Clean up old versions regularly

---

**Congratulations!** You now have a fully functional visual builder integrated with Modula. Users can create beautiful, responsive components without writing a single line of code.
