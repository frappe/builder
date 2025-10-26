# Modula Builder Integration Architecture

## Overview

This document describes how Frappe Builder integrates with Modula as `builder.modula.digital` to provide visual building capabilities for Modula components (Profile Tabs, Widgets, Pages).

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Modula (modula.digital)                        │
│                                                                   │
│  Stack: PHP 8.x + Sngine + Smarty + MySQL + jQuery/Bootstrap    │
│  • Profile system, Widgets, Pages                                │
│  • User authentication via Sngine sessions                       │
│  • Database: modula_builder_artifacts, modula_builder_versions   │
└────────────┬─────────────────────────────────────┬───────────────┘
             │                                     │
        [1] Create/Edit Build                [5] Publish Callback
        POST /api/builder/session             POST modula_callback_url
        {                                     {
          user_id,                              project_id,
          project_id,                           version,
          type: "profile_tab",                  artifacts: {
          jwt_token                               html_url,
        }                                         json_url,
             │                                     tpl_url
             │                                   }
             ↓                                 }
             │                                     ↑
┌────────────┴─────────────────────────────────────┴───────────────┐
│              builder.modula.digital (Frappe Builder)              │
│                                                                   │
│  Stack: Python + Frappe Framework + Vue 3 + TypeScript           │
│  • Visual drag-drop editor (existing)                            │
│  • Component library & templates                                 │
│  • Responsive breakpoints (mobile/tablet/desktop)                │
│  • [NEW] Modula integration layer                                │
│  • [NEW] Export engines (HTML, MDK JSON, Smarty)                 │
└───────────────────────────────────────────────────────────────────┘
```

## Integration Flow

### 1. **Create/Open Build** (Modula → Builder)

**User Action:** Click "Edit Profile Tab" in Modula

**Modula Side:**
```php
// In Modula (PHP)
$jwt_token = create_modula_jwt([
    'user_id' => $user->user_id,
    'project_id' => $project_id,
    'type' => 'profile_tab',
    'exp' => time() + 3600
]);

$builder_url = "https://builder.modula.digital/app/builder?token={$jwt_token}&project={$project_id}";
redirect($builder_url);
```

**Builder Side:**
- Receives JWT token via URL parameter
- Validates token against Modula's public key or validation endpoint
- Creates or loads existing build from MDK JSON
- Opens visual editor

### 2. **Visual Editing** (Builder)

User works in Frappe Builder's existing interface:
- Drag-drop components
- Style with property panels
- Preview responsive breakpoints
- Add interactions
- (Optional) Use AI assistant (Ctrl+K)

### 3. **Publish** (Builder → Modula)

**User Action:** Click "Publish" in Builder

**Builder generates three artifacts:**

#### A) HTML Fragment (Runtime)
```html
<!-- Clean, injectable HTML -->
<div class="profile-tab-content" data-modula-build="b_abc123">
  <style scoped>
    .profile-header {
      display: flex;
      gap: 1rem;
    }
    @media (max-width: 768px) {
      .profile-header { flex-direction: column; }
    }
  </style>

  <div class="profile-header">
    <img src="{{user.avatar}}" alt="{{user.name}}" />
    <h1>{{user.name}}</h1>
  </div>
</div>
```

Stored:
- **DB:** `modula_builder_artifacts` table
- **File:** `/content/snippets/{project_id}/{version}/fragment.html`

#### B) MDK JSON (Re-hydration Schema)
```json
{
  "version": "1.0.0",
  "type": "profile_tab",
  "project_id": "proj_123",
  "metadata": {
    "name": "Profile Header",
    "created_at": "2025-10-26T10:30:00Z",
    "author": "user_456"
  },
  "tree": {
    "blockId": "root",
    "element": "div",
    "attributes": {
      "class": "profile-tab-content",
      "data-modula-build": "b_abc123"
    },
    "baseStyles": {
      "display": "flex",
      "gap": "1rem"
    },
    "mobileStyles": {
      "flexDirection": "column"
    },
    "children": [
      {
        "blockId": "img_1",
        "element": "img",
        "attributes": {
          "src": "{{user.avatar}}",
          "alt": "{{user.name}}"
        }
      }
    ]
  },
  "variables": {
    "user.avatar": { "type": "image", "source": "sngine_user.avatar" },
    "user.name": { "type": "text", "source": "sngine_user.name" }
  },
  "responsive": {
    "breakpoints": {
      "mobile": 768,
      "tablet": 1024
    }
  },
  "assets": [
    { "type": "image", "url": "/content/themes/default/images/avatar.png" }
  ]
}
```

Stored:
- **DB:** `modula_builder_artifacts` (blob column)
- **File:** `/content/snippets/{project_id}/{version}/build.mdk.json`

#### C) Smarty Template (Optional)
```smarty
{* Generated Smarty partial for Profile Tab *}
{* Build: b_abc123 | Version: 1.0.0 *}

<div class="profile-tab-content" data-modula-build="b_abc123">
  <style scoped>
    .profile-header { display: flex; gap: 1rem; }
    @media (max-width: 768px) {
      .profile-header { flex-direction: column; }
    }
  </style>

  <div class="profile-header">
    <img src="{$user->_data.user_picture}" alt="{$user->_data.user_firstname} {$user->_data.user_lastname}" />
    <h1>{$user->_data.user_firstname} {$user->_data.user_lastname}</h1>
  </div>
</div>
```

Stored:
- **File:** `/content/themes/default/templates/blocks/profile_tab_{project_id}.tpl`

### 4. **Callback to Modula**

Builder sends publish confirmation:

```http
POST https://modula.digital/api/forge/publish_callback
Authorization: Bearer {builder_jwt}
Content-Type: application/json

{
  "project_id": "proj_123",
  "build_code": "b_abc123",
  "version": "1.0.0",
  "artifacts": {
    "html_fragment": "/content/snippets/proj_123/1.0.0/fragment.html",
    "mdk_json": "/content/snippets/proj_123/1.0.0/build.mdk.json",
    "smarty_tpl": "/content/themes/default/templates/blocks/profile_tab_proj_123.tpl"
  },
  "status": "published",
  "timestamp": "2025-10-26T10:35:00Z"
}
```

### 5. **Modula Integration**

Modula receives callback and integrates:

```php
// In profile page template
{include file="blocks/profile_tab_{$project.id}.tpl"}

// Or direct HTML injection
echo file_get_contents("/content/snippets/{$project_id}/latest/fragment.html");
```

## Authentication System

### JWT Flow

**Modula creates JWT:**
```php
// Modula (PHP)
use Firebase\JWT\JWT;

$payload = [
    'iss' => 'https://modula.digital',
    'aud' => 'https://builder.modula.digital',
    'sub' => $user->user_id,
    'project_id' => $project_id,
    'type' => 'profile_tab',
    'permissions' => ['edit', 'publish'],
    'iat' => time(),
    'exp' => time() + 3600 // 1 hour
];

$jwt = JWT::encode($payload, MODULA_PRIVATE_KEY, 'RS256');
```

**Builder validates JWT:**
```python
# Builder (Python)
import jwt
import requests

def validate_modula_token(token):
    try:
        # Option 1: Validate with Modula's public key
        public_key = get_modula_public_key()
        payload = jwt.decode(token, public_key, algorithms=['RS256'])

        # Option 2: Validate via Modula API
        response = requests.post(
            'https://modula.digital/api/auth/validate',
            json={'token': token}
        )

        if response.status_code == 200:
            return response.json()

        return None
    except jwt.InvalidTokenError:
        return None
```

## Database Schema

### modula_builder_artifacts (Modula MySQL)

```sql
CREATE TABLE modula_builder_artifacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(50) NOT NULL,
    build_code VARCHAR(50) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    type ENUM('profile_tab', 'widget', 'page', 'component', 'layout') NOT NULL,
    name VARCHAR(255),

    -- Artifact storage
    html_fragment TEXT,
    html_path VARCHAR(500),
    mdk_json MEDIUMTEXT,
    mdk_path VARCHAR(500),
    smarty_tpl TEXT,
    smarty_path VARCHAR(500),

    -- Metadata
    mime_type VARCHAR(100) DEFAULT 'text/html',
    file_size INT,
    checksum VARCHAR(64),

    -- Ownership & status
    created_by INT NOT NULL,
    status ENUM('draft', 'published', 'archived') DEFAULT 'draft',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,

    -- Indexes
    INDEX idx_project (project_id),
    INDEX idx_build (build_code),
    INDEX idx_created_by (created_by),
    INDEX idx_status (status),

    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### modula_builder_versions (Version History)

```sql
CREATE TABLE modula_builder_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    artifact_id INT NOT NULL,
    version VARCHAR(20) NOT NULL,
    snapshot_json MEDIUMTEXT NOT NULL,
    change_summary VARCHAR(500),
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_artifact (artifact_id),
    UNIQUE KEY unique_artifact_version (artifact_id, version),

    FOREIGN KEY (artifact_id) REFERENCES modula_builder_artifacts(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## API Endpoints

### Builder Endpoints (builder.modula.digital)

#### 1. Create/Open Build Session
```http
GET /app/builder?token={jwt}&project={project_id}
```

Response: Opens visual editor

#### 2. Validate Token
```http
POST /api/modula/auth/validate
Content-Type: application/json

{
  "token": "eyJhbGc..."
}
```

Response:
```json
{
  "valid": true,
  "user_id": "user_456",
  "project_id": "proj_123",
  "permissions": ["edit", "publish"]
}
```

#### 3. Export Build
```http
POST /api/modula/export
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "project_id": "proj_123",
  "format": "html|json|tpl|all",
  "options": {
    "minify": true,
    "inline_css": true,
    "scoped": true
  }
}
```

Response:
```json
{
  "build_code": "b_abc123",
  "exports": {
    "html": "<div class='profile-tab'>...</div>",
    "json": { "version": "1.0.0", ... },
    "tpl": "{* Smarty template *}..."
  }
}
```

#### 4. Publish Build
```http
POST /api/modula/publish
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "project_id": "proj_123",
  "version": "1.0.1",
  "callback_url": "https://modula.digital/api/forge/publish_callback",
  "options": {
    "create_version": true,
    "deploy_to_file": true
  }
}
```

Response:
```json
{
  "success": true,
  "build_code": "b_abc123",
  "version": "1.0.1",
  "artifacts": {
    "html_url": "/content/snippets/proj_123/1.0.1/fragment.html",
    "json_url": "/content/snippets/proj_123/1.0.1/build.mdk.json",
    "tpl_url": "/content/themes/default/templates/blocks/profile_tab_proj_123.tpl"
  },
  "callback_sent": true
}
```

### Modula Endpoints (modula.digital)

#### 1. Publish Callback
```http
POST /api/forge/publish_callback
Authorization: Bearer {builder_jwt}
Content-Type: application/json

{
  "project_id": "proj_123",
  "build_code": "b_abc123",
  "version": "1.0.1",
  "artifacts": { ... }
}
```

#### 2. Token Validation
```http
POST /api/auth/validate
Content-Type: application/json

{
  "token": "eyJhbGc..."
}
```

## File System Structure

```
/content/
  └── snippets/
      └── {project_id}/
          ├── latest/                    # Symlink to latest version
          │   ├── fragment.html
          │   ├── build.mdk.json
          │   └── metadata.json
          ├── 1.0.0/
          │   ├── fragment.html
          │   ├── build.mdk.json
          │   └── metadata.json
          └── 1.0.1/
              ├── fragment.html
              ├── build.mdk.json
              └── metadata.json

/content/themes/default/templates/blocks/
  ├── profile_tab_proj_123.tpl
  ├── widget_proj_456.tpl
  └── ...
```

## MDK JSON Schema

```typescript
interface MDKSchema {
  version: string;               // "1.0.0"
  type: BuildType;              // "profile_tab" | "widget" | "page" | ...
  project_id: string;

  metadata: {
    name: string;
    description?: string;
    created_at: string;         // ISO 8601
    author: string;             // user_id
    tags?: string[];
  };

  tree: BlockNode;              // Root block node

  variables: {                  // Dynamic data bindings
    [key: string]: {
      type: "text" | "image" | "url" | "number";
      source: string;           // e.g., "sngine_user.avatar"
      default?: any;
    };
  };

  responsive: {
    breakpoints: {
      mobile: number;           // 768
      tablet: number;           // 1024
    };
  };

  assets: Asset[];              // Images, fonts, etc.

  scripts?: {
    interactions: Interaction[];
    custom?: string;            // Custom JS
  };
}

interface BlockNode {
  blockId: string;
  element: string;              // "div", "img", "button", etc.
  attributes: Record<string, string>;
  baseStyles: Record<string, string>;
  mobileStyles?: Record<string, string>;
  tabletStyles?: Record<string, string>;
  children?: BlockNode[];
  dataBinding?: string;         // Reference to variables key
}
```

## Security Considerations

1. **JWT Validation**
   - Always validate JWT signature
   - Check expiration time
   - Verify audience and issuer
   - Rate limit validation endpoint

2. **CSRF Protection**
   - Builder inherits Frappe's CSRF tokens
   - Modula validates via Sngine's CSRF system
   - Cross-origin requests use JWT bearer tokens

3. **Content Security**
   - Sanitize HTML fragments before storage
   - Validate JSON schema before parsing
   - Escape Smarty template variables
   - Use scoped CSS to prevent style leaks

4. **File System**
   - Store artifacts outside webroot when possible
   - Use content-hash versioning
   - Implement access control on snippet URLs
   - Regular cleanup of old versions

## Deployment

### Builder (builder.modula.digital)

```bash
# Subdomain setup
# DNS: builder.modula.digital → Builder server IP

# Nginx config
server {
    server_name builder.modula.digital;

    location / {
        proxy_pass http://localhost:8000;  # Frappe port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    ssl_certificate /etc/letsencrypt/live/builder.modula.digital/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/builder.modula.digital/privkey.pem;
}

# Frappe site setup
bench new-site builder.modula.digital
bench --site builder.modula.digital install-app builder
bench --site builder.modula.digital set-config modula_api_url "https://modula.digital"
```

### Modula Integration

```php
// In Modula's config
define('BUILDER_URL', 'https://builder.modula.digital');
define('BUILDER_API_URL', 'https://builder.modula.digital/api/modula');
define('BUILDER_JWT_KEY', '/path/to/private.key');

// Initialize builder session
function open_builder($project_id, $type = 'profile_tab') {
    global $user;

    $jwt = create_builder_jwt([
        'user_id' => $user->user_id,
        'project_id' => $project_id,
        'type' => $type
    ]);

    $url = BUILDER_URL . "/app/builder?token={$jwt}&project={$project_id}";
    redirect($url);
}
```

## Version Control Flow

```
User edits in Builder
    ↓
Click "Save as Version"
    ↓
Builder creates version snapshot
    ↓
Stores in modula_builder_versions
    ↓
User can rollback anytime
    ↓
Click "Publish Version 1.0.0"
    ↓
Deploys that specific version
```

## Next Steps

1. ✅ Create this architecture document
2. ⏳ Implement authentication bridge
3. ⏳ Create MDK JSON exporter
4. ⏳ Create HTML fragment exporter
5. ⏳ Create Smarty template generator
6. ⏳ Build publish API endpoints
7. ⏳ Set up database tables
8. ⏳ Create deployment scripts
9. ⏳ Write integration tests
10. ⏳ Documentation for Modula developers

## References

- Frappe Builder Docs: https://frappe.io/builder
- Sngine Framework: (Modula's base)
- Smarty Templates: https://www.smarty.net/docs/
- JWT Best Practices: https://tools.ietf.org/html/rfc8725
