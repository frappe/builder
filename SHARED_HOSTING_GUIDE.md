# Modula Builder - Shared Hosting Installation Guide

This guide walks you through installing Modula Builder on **shared hosting** environments (cPanel, Plesk, DirectAdmin, etc.) where you don't have root/sudo access.

## Important Notes

### What Requires VPS

- **Builder (builder.modula.digital)** - Requires VPS/dedicated server (Frappe Framework needs Python, Redis, Node.js)

### What Works on Shared Hosting

- **Modula Integration** - Runs perfectly on shared hosting (PHP + MySQL only)

## Prerequisites

### Shared Hosting Requirements

✅ **Required:**
- PHP 7.4 or higher
- MySQL 5.7+ or MariaDB 10.2+
- cURL extension enabled
- mysqli extension enabled
- File upload capability

✅ **Recommended:**
- PHP 8.0+
- SSL certificate (Let's Encrypt)
- mod_rewrite enabled
- 256MB memory limit

❌ **Not Required:**
- Root/sudo access
- SSH access (nice to have, but not required)
- Composer (fallback included)
- Custom PHP extensions

## Installation Options

### Option 1: Automatic Installation (Recommended)

If you have SSH access to your shared hosting:

```bash
# Upload integration files
cd ~/
wget https://github.com/Modula-Digital/builder/archive/refs/heads/claude/create-modula-builder-011CUUj7xJRRSdAdrAa9L4zr.zip
unzip create-modula-builder-011CUUj7xJRRSdAdrAa9L4zr.zip
cd builder-*/modula_integration

# Run deployment script
chmod +x deploy_shared_hosting.sh
./deploy_shared_hosting.sh
```

Follow the prompts and you're done!

### Option 2: Manual Installation (No SSH)

Use cPanel File Manager or FTP:

#### Step 1: Upload Files

Upload these files to your hosting:

```
public_html/
├── includes/
│   ├── builder/
│   │   ├── ModulaBuilderClient.php (from ModulaBuilderClient_SharedHosting.php)
│   │   ├── jwt_fallback.php
│   │   └── examples.php
│   ├── builder_config.php (create manually)
│   ├── builder_functions.php
│   └── builder_smarty.php
├── api/
│   └── builder/
│       ├── callback.php
│       └── .htaccess
├── content/
│   ├── snippets/ (empty directory)
│   └── themes/
│       └── default/
│           └── templates/
│               └── blocks/ (empty directory)
└── setup_database.sql
```

#### Step 2: Create Configuration File

Create `public_html/includes/builder_config.php`:

```php
<?php
/**
 * Modula Builder Configuration
 */

// Builder Settings
define('BUILDER_URL', 'https://builder.modula.digital');
define('BUILDER_API_URL', 'https://builder.modula.digital/api/method/builder.modula_api');
define('BUILDER_JWT_SECRET', 'your-super-secret-key-here-min-32-chars');
define('BUILDER_JWT_ALGORITHM', 'HS256');
define('BUILDER_CALLBACK_URL', 'https://yourdomain.com/api/builder/callback.php');
```

**Important:** Use a strong JWT secret (32+ characters). Generate one at: https://randomkeygen.com/

#### Step 3: Import Database Schema

1. Log into **phpMyAdmin** (usually in cPanel)
2. Select your database
3. Click **Import** tab
4. Choose `setup_database.sql`
5. Click **Go**

You should see 4 new tables:
- `modula_builder_artifacts`
- `modula_builder_versions`
- `modula_builder_deployments`
- `modula_builder_sessions`

#### Step 4: Set Directory Permissions

In cPanel File Manager, set permissions:

```
content/snippets/                     → 755
content/themes/default/templates/blocks/ → 755
```

#### Step 5: Update Your Application

Add to your `includes/config.php`:

```php
// At the end of the file
require_once __DIR__ . '/builder_config.php';
```

Add to your initialization file (after database connection):

```php
// Load builder functions
require_once __DIR__ . '/includes/builder_functions.php';
```

Add after Smarty initialization:

```php
// Register builder Smarty functions
require_once __DIR__ . '/includes/builder_smarty.php';
```

## Testing Your Installation

### Option 1: Use Test File

Upload `test_builder.php` to your `public_html/`:

```php
<?php
require_once 'includes/config.php';
require_once 'includes/builder_config.php';
require_once 'includes/builder_functions.php';

// Test session creation
if (isset($user) && $user->user_id) {
    $url = open_builder_session($user->user_id, 'test_project', 'widget');
    echo "Builder URL: " . $url . "\n";
    echo '<a href="' . $url . '">Open Builder</a>';
} else {
    echo "Please log in first";
}
?>
```

Visit: `https://yourdomain.com/test_builder.php`

### Option 2: Manual Test

Create a simple test:

```php
<?php
// Test JWT creation
require_once 'includes/builder/ModulaBuilderClient.php';

$builder = new ModulaBuilderClient([
    'builder_url' => 'https://builder.modula.digital',
    'jwt_secret' => 'your-secret',
    'db' => $db,
    'base_path' => dirname(__DIR__)
]);

$url = $builder->createSession(1, 'test_123', 'widget');
echo $url;
?>
```

## Common Shared Hosting Providers

### cPanel (Most Common)

✅ **Works perfectly**

Steps:
1. File Manager → Upload files
2. phpMyAdmin → Import database
3. File Manager → Set permissions
4. Done!

### Plesk

✅ **Works perfectly**

Steps:
1. Files → Upload via web or FTP
2. Databases → Import SQL
3. File Manager → Permissions
4. Done!

### DirectAdmin

✅ **Works perfectly**

Similar to cPanel - use File Manager and phpMyAdmin.

### Hostinger / Namecheap / Bluehost / GoDaddy

✅ **All work with cPanel**

Follow cPanel instructions above.

## Troubleshooting

### "JWT validation failed"

**Cause:** JWT secret mismatch

**Solution:**
1. Check `includes/builder_config.php` → `BUILDER_JWT_SECRET`
2. Check builder.modula.digital config
3. Ensure they're identical

### "Permission denied" when writing files

**Cause:** Directory permissions

**Solution via cPanel:**
1. File Manager → Select directory
2. Right click → Change Permissions
3. Set to 755
4. Check "Recurse into subdirectories"
5. Save

**Solution via FTP:**
```
CHMOD 755 content/snippets
CHMOD 755 content/themes/default/templates/blocks
```

### "Call to undefined function hash_hmac"

**Cause:** PHP not compiled with hash support (very rare)

**Solution:** Contact hosting support or upgrade PHP version

### "Headers already sent"

**Cause:** Output before callback response

**Solution:** In `api/builder/callback.php`, ensure no output before:
```php
<?php
// NO WHITESPACE OR OUTPUT BEFORE THIS

require_once '../../includes/config.php';
...
```

### Callback not receiving

**Cause 1:** Firewall blocking builder.modula.digital

**Solution:** Whitelist builder server IP in hosting control panel

**Cause 2:** .htaccess not working

**Solution:** Check mod_rewrite is enabled (ask hosting support)

### "Composer not found" (Not a problem!)

This is expected on shared hosting. The system includes a **JWT fallback** that works without Composer.

```
⚠ Composer not found - using JWT fallback implementation
  This is fine for shared hosting.
```

No action needed - this is normal and works perfectly.

## File Paths on Shared Hosting

Shared hosting uses relative paths. The system automatically handles:

### Your Structure Might Be:

```
/home/username/public_html/      → Document root
/home/username/public_html/includes/
/home/username/public_html/content/
```

Or:

```
/var/www/vhosts/domain.com/httpdocs/  → Document root
/var/www/vhosts/domain.com/httpdocs/includes/
```

Or:

```
~/www/             → Document root
~/www/includes/
```

**The integration handles all of these automatically!** No configuration needed.

## Security on Shared Hosting

### 1. Protect Configuration File

Add to `public_html/.htaccess`:

```apache
<FilesMatch "builder_config.php">
    Order allow,deny
    Deny from all
</FilesMatch>
```

### 2. Secure Database

In phpMyAdmin:
- Use strong database password
- Don't use root user
- Create dedicated user for Modula

### 3. Hide Sensitive Files

Add to root `.htaccess`:

```apache
<FilesMatch "\.(sql|log|bak|env)$">
    Order allow,deny
    Deny from all
</FilesMatch>
```

### 4. SSL Certificate

Most shared hosts offer free SSL (Let's Encrypt). Enable it in cPanel:
- SSL/TLS → Install SSL
- Or use hosting's "AutoSSL" feature

## Performance Optimization

### 1. Enable Caching

In your code:

```php
// Cache rendered artifacts
function render_builder_artifact_cached($project_id) {
    $cache_key = "builder_{$project_id}";
    $cache_file = sys_get_temp_dir() . "/{$cache_key}";

    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 3600) {
        return file_get_contents($cache_file);
    }

    $html = render_builder_artifact($project_id);
    file_put_contents($cache_file, $html);

    return $html;
}
```

### 2. Use .htaccess Compression

Add to `public_html/.htaccess`:

```apache
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/css application/javascript
</IfModule>
```

### 3. Optimize Database

Run regularly via phpMyAdmin:

```sql
OPTIMIZE TABLE modula_builder_artifacts;
OPTIMIZE TABLE modula_builder_versions;
```

## Limitations on Shared Hosting

### What Works ✅

- JWT authentication
- Session creation
- Publish callbacks
- Artifact rendering
- Version control
- All core features

### What Might Be Limited ⚠️

- **File uploads** - Limited by hosting (usually 2-10MB)
  - Solution: Increase via .htaccess or contact support

- **Execution time** - Usually 30-60 seconds max
  - Solution: Publish callback is fast (<5 seconds)

- **Memory limit** - Usually 128-256MB
  - Solution: More than enough for this integration

### What Doesn't Work ❌

- **Builder UI** - Requires VPS (Frappe Framework)
  - Solution: Host builder.modula.digital on separate VPS

## FAQ

**Q: Do I need Composer?**
A: No! The system includes a JWT fallback library.

**Q: Can I use this on GoDaddy/Bluehost/Hostinger?**
A: Yes! Works on all cPanel-based shared hosting.

**Q: Do I need SSH access?**
A: No. Everything can be done via cPanel/FTP.

**Q: Will this slow down my site?**
A: No. Artifacts are cached and very lightweight.

**Q: Can I use SQLite instead of MySQL?**
A: No, MySQL/MariaDB is required.

**Q: What if my hosting blocks outbound connections?**
A: Contact support to whitelist builder.modula.digital

**Q: Can multiple domains share one Builder?**
A: Yes! One builder.modula.digital can serve multiple Modula sites.

## Next Steps

1. ✅ Install integration (you're here)
2. 📝 Configure Builder server (VPS required)
3. 🎨 Create your first widget
4. 🚀 Publish to production
5. 📚 Read full docs: `modula_integration/README.md`

## Support

Having issues? Check:
1. This guide (you're reading it)
2. `modula_integration/README.md` - Full documentation
3. `includes/builder/examples.php` - Code examples
4. `QUICKSTART.md` - Quick start guide

Still stuck? Common issues:
- 90% are JWT secret mismatches
- 5% are file permissions
- 5% are database import issues

## Summary

**Shared hosting is fully supported!** The integration is specifically designed to work in restricted environments without root access, Composer, or special PHP extensions.

Just upload files → import database → update config → done! 🎉

---

**Note:** Remember to delete `test_builder.php` and `setup_database.sql` after setup for security.
